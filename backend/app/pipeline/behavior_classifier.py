"""
Rule-based behavior classifier.

Classifies head pose into observable behavior categories using
simple, transparent threshold logic. No neural network — the rules
are explicit and auditable.

This is intentionally simple. The value is in the transparency:
- Teachers can understand WHY a behavior was classified
- Thresholds can be adjusted without retraining anything
- The system is honest about what it measures (head pose, not "attention")
"""

from dataclasses import dataclass

from app.models.analysis import BehaviorType
from app.pipeline.head_pose_estimator import HeadPose


@dataclass
class ClassificationResult:
    """Result of classifying a head pose."""
    behavior: BehaviorType
    head_yaw: float
    head_pitch: float
    head_roll: float
    confidence: float


class BehaviorClassifier:
    """
    Classifies head pose into behavior categories.

    Thresholds:
        yaw_threshold:   If |yaw| > threshold → looking_away
        pitch_threshold: If pitch < threshold → head_down

    Default thresholds are based on published research on head pose
    and attention estimation in classroom settings.
    """

    def __init__(
        self,
        yaw_threshold: float = 30.0,
        pitch_threshold: float = -20.0,
    ):
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold

    def classify(
        self, pose: HeadPose, detection_confidence: float
    ) -> ClassificationResult:
        """
        Classify a head pose into a behavior category.

        Priority order:
        1. looking_away (large yaw — turned away from the front)
        2. head_down (low pitch — looking down)
        3. attentive (within both thresholds)
        """
        if abs(pose.yaw) > self.yaw_threshold:
            behavior = BehaviorType.LOOKING_AWAY
        elif pose.pitch < self.pitch_threshold:
            behavior = BehaviorType.HEAD_DOWN
        else:
            behavior = BehaviorType.ATTENTIVE

        return ClassificationResult(
            behavior=behavior,
            head_yaw=pose.yaw,
            head_pitch=pose.pitch,
            head_roll=pose.roll,
            confidence=detection_confidence,
        )
