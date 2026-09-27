"""
Meeting Provider Abstraction Layer.
The AI system must not depend directly on Google Meet.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from enum import Enum


class MeetingStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class MeetingParticipant:
    """A participant in a meeting."""
    participant_id: str
    display_name: Optional[str] = None
    has_video: bool = False
    has_audio: bool = False


class MeetingProvider(ABC):
    """
    Abstract base class for meeting platform integrations.
    Implementations: GoogleMeetProvider, ZoomProvider (future), TeamsProvider (future)
    """

    @abstractmethod
    async def connect(self, meeting_url: str, **kwargs) -> bool:
        """Connect to a meeting."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the meeting."""
        pass

    @abstractmethod
    async def get_status(self) -> MeetingStatus:
        """Get current connection status."""
        pass

    @abstractmethod
    async def get_participants(self) -> List[MeetingParticipant]:
        """Get list of current participants."""
        pass

    @abstractmethod
    async def start_video_capture(
        self,
        participant_id: Optional[str] = None,
        on_frame: Optional[Callable] = None,
    ) -> bool:
        """
        Start capturing video frames.
        Requires explicit authorization.
        """
        pass

    @abstractmethod
    async def stop_video_capture(self) -> bool:
        """Stop video capture."""
        pass

    @abstractmethod
    async def get_meeting_info(self) -> Dict:
        """Get meeting metadata."""
        pass
