"""
WebSocket handler for real-time attention event streaming.
Implements reconnect handling, heartbeat, and duplicate event prevention.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # {session_id: set of WebSocket connections}
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._last_heartbeat: Dict[int, float] = {}
        # Track sent event IDs per connection to prevent duplicates
        self._sent_events: Dict[int, set] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
        self._sent_events[id(websocket)] = set()
        logger.info(f"WebSocket connected for session {session_id}. "
                     f"Total: {len(self._connections[session_id])}")

    def disconnect(self, websocket: WebSocket, session_id: int):
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
        self._sent_events.pop(id(websocket), None)
        logger.info(f"WebSocket disconnected from session {session_id}")

    async def broadcast_to_session(self, session_id: int, message: dict):
        """Broadcast a message to all connections for a session."""
        connections = self._connections.get(session_id, set())
        if not connections:
            return

        # Create event ID for dedup
        event_id = f"{message.get('event_type', '')}_{message.get('participant_id', '')}_{message.get('timestamp', '')}"

        stale = set()
        for ws in connections:
            ws_id = id(ws)
            sent = self._sent_events.get(ws_id, set())

            # Skip duplicate events
            if event_id in sent:
                continue

            try:
                await ws.send_json(message)
                sent.add(event_id)
                # Limit memory: keep last 1000 event IDs
                if len(sent) > 1000:
                    sent.clear()
            except Exception as e:
                logger.warning(f"WebSocket send failed: {e}")
                stale.add(ws)

        # Clean stale connections
        for ws in stale:
            self.disconnect(ws, session_id)

    async def send_heartbeat(self, session_id: int):
        """Send heartbeat to keep connections alive."""
        connections = self._connections.get(session_id, set())
        stale = set()
        for ws in connections:
            try:
                await ws.send_json({"type": "heartbeat", "timestamp": time.time()})
            except Exception:
                stale.add(ws)

        for ws in stale:
            self.disconnect(ws, session_id)

    def get_active_sessions(self) -> list:
        """Get list of session IDs with active connections."""
        return list(self._connections.keys())

    def get_connection_count(self, session_id: int = None) -> int:
        """Get number of active connections."""
        if session_id:
            return len(self._connections.get(session_id, set()))
        return sum(len(v) for v in self._connections.values())


# Global connection manager
ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """WebSocket endpoint handler for live session streaming."""
    await ws_manager.connect(websocket, session_id)

    try:
        while True:
            # Wait for messages from client
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,
                )
                message = json.loads(data)

                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                
                elif msg_type == "video_frame":
                    # Handle incoming video frame
                    participant_id = message.get("participant_id")
                    b64_data = message.get("data")
                    
                    if participant_id and b64_data:
                        try:
                            # Parse base64
                            import base64
                            import cv2
                            import numpy as np
                            from ..services.video_service import video_service
                            
                            # Remove data URL scheme if present
                            if "," in b64_data:
                                b64_data = b64_data.split(",")[1]
                                
                            image_bytes = base64.b64decode(b64_data)
                            np_arr = np.frombuffer(image_bytes, np.uint8)
                            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                            
                            if frame is not None:
                                # Process frame asynchronously
                                asyncio.create_task(
                                    video_service.process_frame(session_id, participant_id, frame)
                                )
                                
                        except Exception as e:
                            logger.error(f"Error processing video frame: {e}")

            except asyncio.TimeoutError:
                # Send heartbeat on timeout
                await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        ws_manager.disconnect(websocket, session_id)
