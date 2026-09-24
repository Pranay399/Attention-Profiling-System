import base64
import time

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.logging import get_logger
from app.pipeline.live_processor import LiveProcessor

logger = get_logger("api.live")
router = APIRouter()


@router.websocket("/ws")
async def live_monitoring(websocket: WebSocket):
    """
    WebSocket endpoint that receives image frames, processes them, 
    and returns real-time behavior observations.
    """
    await websocket.accept()
    logger.info("websocket_client_connected", client=websocket.client)

    processor = LiveProcessor()

    try:
        while True:
            # Receive text data (Base64 JPEG)
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
                continue
                
            if data.startswith("data:image/jpeg;base64,"):
                # Decode Base64 string to bytes
                base64_data = data.split(",", 1)[1]
                img_bytes = base64.b64decode(base64_data)
                
                # Convert bytes to numpy array then to BGR image
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Process frame
                    observations = processor.process_frame(frame, time.time())
                    
                    # Send results back
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "observations", 
                            "data": observations
                        })

    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected", client=websocket.client)
    except Exception as e:
        logger.error("websocket_error", error=str(e), exc_info=True)
    finally:
        processor.close()
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except RuntimeError:
                pass
