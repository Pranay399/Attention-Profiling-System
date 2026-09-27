"""
Google Meet provider implementation.
Uses authorized browser capture mechanism (Screen Capture API / getDisplayMedia).
Does NOT scrape Google Meet DOM or bypass permissions.
"""

import logging
from typing import Optional, Dict, List, Callable

from .base import MeetingProvider, MeetingStatus, MeetingParticipant

logger = logging.getLogger(__name__)


class GoogleMeetProvider(MeetingProvider):
    """
    Google Meet integration using authorized browser capture.

    For the prototype, this uses the Screen Capture API (getDisplayMedia)
    which requires explicit user authorization. The teacher must grant
    permission to share the meeting tab/window.

    This does NOT:
    - Scrape the Google Meet DOM
    - Bypass any permissions
    - Secretly capture participants
    - Use unauthorized browser automation
    - Access microphone/camera without consent
    """

    def __init__(self):
        self.status = MeetingStatus.PENDING
        self.meeting_url: Optional[str] = None
        self.meeting_id: Optional[str] = None
        self.participants: List[MeetingParticipant] = []
        self._is_capturing = False
        self._frame_callback: Optional[Callable] = None

    async def connect(self, meeting_url: str, **kwargs) -> bool:
        """
        Connect to a Google Meet session.
        In production, this would coordinate with a browser extension
        that uses the authorized Screen Capture API.
        """
        self.meeting_url = meeting_url
        # Extract meeting ID from URL
        if "meet.google.com" in meeting_url:
            parts = meeting_url.rstrip("/").split("/")
            self.meeting_id = parts[-1] if parts else None

        self.status = MeetingStatus.CONNECTED
        logger.info(f"Connected to Google Meet: {self.meeting_id}")
        return True

    async def disconnect(self) -> bool:
        """Disconnect from Google Meet."""
        self.status = MeetingStatus.DISCONNECTED
        self._is_capturing = False
        logger.info(f"Disconnected from Google Meet: {self.meeting_id}")
        return True

    async def get_status(self) -> MeetingStatus:
        """Get connection status."""
        return self.status

    async def get_participants(self) -> List[MeetingParticipant]:
        """
        Get meeting participants.
        In production, this would be populated by the browser extension
        observing participant joins/leaves through authorized means.
        """
        return self.participants

    def add_participant(self, participant_id: str, display_name: str = None):
        """Add a participant (called by the browser capture layer)."""
        p = MeetingParticipant(
            participant_id=participant_id,
            display_name=display_name,
            has_video=True,
        )
        self.participants.append(p)
        return p

    async def start_video_capture(
        self,
        participant_id: Optional[str] = None,
        on_frame: Optional[Callable] = None,
    ) -> bool:
        """
        Start video capture using authorized browser Screen Capture API.
        The teacher must explicitly authorize this capture.
        """
        if self.status != MeetingStatus.CONNECTED:
            logger.error("Cannot start capture: not connected")
            return False

        self._is_capturing = True
        self._frame_callback = on_frame
        logger.info("Video capture started (authorized browser capture)")
        return True

    async def stop_video_capture(self) -> bool:
        """Stop video capture."""
        self._is_capturing = False
        self._frame_callback = None
        logger.info("Video capture stopped")
        return True

    async def get_meeting_info(self) -> Dict:
        """Get meeting metadata."""
        return {
            "provider": "google_meet",
            "meeting_url": self.meeting_url,
            "meeting_id": self.meeting_id,
            "status": self.status.value,
            "participant_count": len(self.participants),
            "is_capturing": self._is_capturing,
        }
