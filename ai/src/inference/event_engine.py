"""
Temporal smoothing and event detection engine.

Implements:
- EventDetector: Detects attention state changes
- EventSmoother: Rolling window temporal smoothing
- CooldownManager: Prevents alert flooding
- AlertManager: Event dispatch with deduplication
"""

import time
import logging
from collections import deque
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    ATTENTION_DROP = "attention_drop"
    ATTENTION_RECOVERED = "attention_recovered"
    FACE_NOT_VISIBLE = "face_not_visible"
    INSUFFICIENT_VISUAL_DATA = "insufficient_visual_data"
    REPEATED_ATTENTION_DROP = "repeated_attention_drop"


@dataclass
class AttentionEvent:
    """A detected attention event."""
    event_type: str
    participant_id: str
    probability: float
    duration_seconds: float
    timestamp: str
    model_version: str
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type,
            "participant_id": self.participant_id,
            "probability": round(self.probability, 4),
            "duration_seconds": round(self.duration_seconds, 2),
            "timestamp": self.timestamp,
            "model_version": self.model_version,
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }


@dataclass
class SmoothingConfig:
    """Configuration for temporal smoothing — all thresholds are configurable."""
    window_size: int = 10  # Number of recent predictions to consider
    inattentive_threshold: float = 0.65  # Probability above which = inattentive
    persistence_seconds: float = 5.0  # How long state must persist before event
    confidence_threshold: float = 0.5  # Minimum confidence to emit event
    cooldown_seconds: float = 30.0  # Cooldown between same event type per participant
    recovery_threshold: float = 0.4  # Inattentive prob below this = recovered
    recovery_persistence_seconds: float = 3.0  # How long recovery must persist
    face_missing_seconds: float = 10.0  # Face not visible timeout
    repeated_drop_count: int = 3  # N drops within repeated_drop_window = repeated
    repeated_drop_window_seconds: float = 300.0  # Window for repeated drops (5 min)


class EventSmoother:
    """
    Applies temporal smoothing to raw per-frame attention predictions.
    Maintains a rolling window of recent predictions per participant.
    """

    def __init__(self, config: SmoothingConfig):
        self.config = config
        # Per-participant prediction buffers: {participant_id: deque of (timestamp, probability)}
        self._buffers: Dict[str, deque] = {}

    def add_prediction(
        self, participant_id: str, inattentive_prob: float, timestamp: float
    ) -> float:
        """
        Add a new prediction to the buffer and return the smoothed probability.

        Args:
            participant_id: Unique participant identifier
            inattentive_prob: Raw inattentive probability from model
            timestamp: Unix timestamp of prediction

        Returns:
            Smoothed inattentive probability
        """
        if participant_id not in self._buffers:
            self._buffers[participant_id] = deque(maxlen=self.config.window_size)

        self._buffers[participant_id].append((timestamp, inattentive_prob))
        return self.get_smoothed_probability(participant_id)

    def get_smoothed_probability(self, participant_id: str) -> float:
        """
        Calculate the smoothed probability using exponentially weighted average.
        More recent predictions are weighted higher.
        """
        buffer = self._buffers.get(participant_id)
        if not buffer:
            return 0.0

        # Exponentially weighted moving average
        probabilities = [p for _, p in buffer]
        n = len(probabilities)
        if n == 0:
            return 0.0

        # Weights: more recent = higher weight
        weights = np.array([2 ** (i / n) for i in range(n)])
        weights = weights / weights.sum()

        return float(np.average(probabilities, weights=weights))

    def get_buffer_duration(self, participant_id: str) -> float:
        """Get the time span covered by the buffer in seconds."""
        buffer = self._buffers.get(participant_id)
        if not buffer or len(buffer) < 2:
            return 0.0
        return buffer[-1][0] - buffer[0][0]

    def clear_participant(self, participant_id: str):
        """Clear buffer for a participant."""
        self._buffers.pop(participant_id, None)


# Import numpy for EventSmoother (after class definition to avoid issues)
import numpy as np


class CooldownManager:
    """
    Manages event cooldowns to prevent alert flooding.
    Tracks when each event type was last emitted per participant.
    """

    def __init__(self, default_cooldown_seconds: float = 30.0):
        self.default_cooldown = default_cooldown_seconds
        # {(participant_id, event_type): last_emit_timestamp}
        self._cooldowns: Dict[tuple, float] = {}

    def is_in_cooldown(
        self, participant_id: str, event_type: str, current_time: float
    ) -> bool:
        """Check if an event is still in cooldown."""
        key = (participant_id, event_type)
        last_emit = self._cooldowns.get(key)
        if last_emit is None:
            return False
        return (current_time - last_emit) < self.default_cooldown

    def record_event(
        self, participant_id: str, event_type: str, current_time: float
    ):
        """Record that an event was emitted."""
        key = (participant_id, event_type)
        self._cooldowns[key] = current_time

    def set_cooldown(self, cooldown_seconds: float):
        """Update the default cooldown period."""
        self.default_cooldown = cooldown_seconds

    def clear_participant(self, participant_id: str):
        """Clear all cooldowns for a participant."""
        keys_to_remove = [
            k for k in self._cooldowns if k[0] == participant_id
        ]
        for k in keys_to_remove:
            del self._cooldowns[k]


class EventDetector:
    """
    Detects attention events based on smoothed predictions.
    Implements threshold + persistence + confidence gates.
    """

    def __init__(self, config: SmoothingConfig):
        self.config = config
        # Per-participant state tracking
        # {participant_id: {"state": str, "state_start": float, "drop_history": list}}
        self._states: Dict[str, Dict] = {}

    def _get_state(self, participant_id: str) -> Dict:
        """Get or create state tracker for a participant."""
        if participant_id not in self._states:
            self._states[participant_id] = {
                "state": "unknown",
                "state_start": time.time(),
                "drop_history": [],  # timestamps of attention drops
                "face_missing_start": None,
            }
        return self._states[participant_id]

    def detect(
        self,
        participant_id: str,
        smoothed_prob: float,
        confidence: float,
        face_visible: bool,
        current_time: float,
        model_version: str = "attention-v1",
    ) -> Optional[AttentionEvent]:
        """
        Check if the current state warrants an event.

        Args:
            participant_id: Unique participant ID
            smoothed_prob: Smoothed inattentive probability
            confidence: Model confidence
            face_visible: Whether face is detected
            current_time: Current unix timestamp
            model_version: Version of the model producing predictions

        Returns:
            AttentionEvent if an event should be emitted, None otherwise
        """
        state = self._get_state(participant_id)
        timestamp_str = datetime.fromtimestamp(
            current_time, tz=timezone.utc
        ).isoformat()

        # --- Face not visible ---
        if not face_visible:
            if state["face_missing_start"] is None:
                state["face_missing_start"] = current_time
            elif (current_time - state["face_missing_start"]) >= self.config.face_missing_seconds:
                state["state"] = "face_not_visible"
                return AttentionEvent(
                    event_type=EventType.FACE_NOT_VISIBLE,
                    participant_id=participant_id,
                    probability=0.0,
                    duration_seconds=current_time - state["face_missing_start"],
                    timestamp=timestamp_str,
                    model_version=model_version,
                    confidence=0.0,
                )
            return None
        else:
            state["face_missing_start"] = None

        # --- Insufficient confidence ---
        if confidence < self.config.confidence_threshold:
            return AttentionEvent(
                event_type=EventType.INSUFFICIENT_VISUAL_DATA,
                participant_id=participant_id,
                probability=smoothed_prob,
                duration_seconds=0,
                timestamp=timestamp_str,
                model_version=model_version,
                confidence=confidence,
            )

        # --- Attention drop detection ---
        if smoothed_prob >= self.config.inattentive_threshold:
            if state["state"] != "inattentive":
                state["state"] = "inattentive"
                state["state_start"] = current_time

            duration = current_time - state["state_start"]

            if duration >= self.config.persistence_seconds:
                # Check for repeated drops
                drop_history = state["drop_history"]
                drop_history.append(current_time)
                # Clean old entries
                cutoff = current_time - self.config.repeated_drop_window_seconds
                state["drop_history"] = [t for t in drop_history if t > cutoff]

                if len(state["drop_history"]) >= self.config.repeated_drop_count:
                    return AttentionEvent(
                        event_type=EventType.REPEATED_ATTENTION_DROP,
                        participant_id=participant_id,
                        probability=smoothed_prob,
                        duration_seconds=duration,
                        timestamp=timestamp_str,
                        model_version=model_version,
                        confidence=confidence,
                        metadata={"drop_count": len(state["drop_history"])},
                    )

                return AttentionEvent(
                    event_type=EventType.ATTENTION_DROP,
                    participant_id=participant_id,
                    probability=smoothed_prob,
                    duration_seconds=duration,
                    timestamp=timestamp_str,
                    model_version=model_version,
                    confidence=confidence,
                )

        # --- Attention recovery ---
        elif smoothed_prob <= self.config.recovery_threshold:
            if state["state"] == "inattentive":
                state["state"] = "attentive"
                state["state_start"] = current_time
                return AttentionEvent(
                    event_type=EventType.ATTENTION_RECOVERED,
                    participant_id=participant_id,
                    probability=smoothed_prob,
                    duration_seconds=0,
                    timestamp=timestamp_str,
                    model_version=model_version,
                    confidence=confidence,
                )

        return None


class AlertManager:
    """
    Manages the full event pipeline:
    EventSmoother -> EventDetector -> CooldownManager -> Event dispatch

    Integrates all components and provides the main API for the
    real-time pipeline.
    """

    def __init__(self, config: Optional[SmoothingConfig] = None):
        self.config = config or SmoothingConfig()
        self.smoother = EventSmoother(self.config)
        self.detector = EventDetector(self.config)
        self.cooldown = CooldownManager(self.config.cooldown_seconds)

        # Event subscribers (callbacks)
        self._subscribers: List[callable] = []
        self._event_history: deque = deque(maxlen=1000)

    def subscribe(self, callback: callable):
        """Register a callback for new events."""
        self._subscribers.append(callback)

    def process_prediction(
        self,
        participant_id: str,
        inattentive_prob: float,
        confidence: float,
        face_visible: bool,
        model_version: str = "attention-v1",
    ) -> Optional[AttentionEvent]:
        """
        Process a single frame prediction through the full pipeline.

        Frame prediction -> Smoothing -> Detection -> Cooldown check -> Event

        Args:
            participant_id: Unique participant identifier
            inattentive_prob: Raw inattentive probability
            confidence: Model confidence
            face_visible: Whether face is detected in frame
            model_version: Model version string

        Returns:
            AttentionEvent if one should be emitted, None otherwise
        """
        current_time = time.time()

        # 1. Temporal smoothing
        smoothed_prob = self.smoother.add_prediction(
            participant_id, inattentive_prob, current_time
        )

        # 2. Event detection
        event = self.detector.detect(
            participant_id=participant_id,
            smoothed_prob=smoothed_prob,
            confidence=confidence,
            face_visible=face_visible,
            current_time=current_time,
            model_version=model_version,
        )

        if event is None:
            return None

        # 3. Cooldown check
        if self.cooldown.is_in_cooldown(
            participant_id, event.event_type, current_time
        ):
            logger.debug(f"Event {event.event_type} for {participant_id} in cooldown")
            return None

        # 4. Record and dispatch
        self.cooldown.record_event(
            participant_id, event.event_type, current_time
        )
        self._event_history.append(event)

        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

        logger.info(
            f"Event: {event.event_type} | participant={participant_id} | "
            f"prob={event.probability:.2f} | confidence={event.confidence:.2f}"
        )

        return event

    def get_participant_state(self, participant_id: str) -> Dict:
        """Get current state for a participant."""
        smoothed = self.smoother.get_smoothed_probability(participant_id)
        state = self.detector._get_state(participant_id)
        return {
            "participant_id": participant_id,
            "smoothed_inattentive_prob": round(smoothed, 4),
            "current_state": state["state"],
            "state_duration": round(time.time() - state["state_start"], 2),
        }

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events."""
        events = list(self._event_history)[-limit:]
        return [e.to_dict() for e in events]

    def update_config(self, **kwargs):
        """Update smoothing/detection configuration at runtime."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Config updated: {key}={value}")

        # Update cooldown if changed
        if "cooldown_seconds" in kwargs:
            self.cooldown.set_cooldown(kwargs["cooldown_seconds"])
