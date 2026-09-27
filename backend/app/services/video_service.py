"""
Video Processing Service that orchestrates frame processing and feeds the Analysis Service.
"""

import sys
from pathlib import Path
from typing import Dict, Optional
import logging
import numpy as np

# Add project root to path to import meeting
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from meeting.capture.video_processor import FrameProcessor
from .analysis_service import analysis_service
from ..websocket.handler import ws_manager

logger = logging.getLogger(__name__)


class VideoService:
    def __init__(self):
        self.processor = FrameProcessor(target_fps=10)
        self.active_participants = set()

    async def process_frame(self, session_id: int, participant_id: str, frame: np.ndarray):
        """
        Process a raw video frame, extract features, run inference, and broadcast events.
        """
        try:
            # 1. Extract CV features via MediaPipe
            cv_features = self.processor.process_frame(frame)
            
            if cv_features is None:
                # Frame dropped (rate limiting) or no output
                return
                
            # 2. Add to active participants
            self.active_participants.add(participant_id)
            
            # 3. Pass to AnalysisService
            event_dict = analysis_service.process_frame_features(
                participant_id=participant_id,
                cv_features=cv_features
            )
            
            # 4. Broadcast event if detected
            if event_dict:
                await ws_manager.broadcast_to_session(session_id, event_dict)
                
            # 5. Broadcast participant state periodically (every 30 frames or so)
            # In a real system, we'd do this on a timer, but for now we just get it
            # and could broadcast it if we wanted real-time UI updates
            state = analysis_service.get_participant_state(participant_id)
            if state and "current_state" in state:
                state_msg = {
                    "type": "participant_state",
                    "session_id": session_id,
                    **state
                }
                await ws_manager.broadcast_to_session(session_id, state_msg)
                
        except Exception as e:
            logger.error(f"Error in video service processing: {e}")

video_service = VideoService()
