"""
WebSocket Main Application.

Handles real-time WebSocket connections for the platform.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging

from .connection_manager import ConnectionManager
from .event_types import EventType
from ..config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Networking AI WebSocket Service",
    description="Real-time WebSocket service for the Networking AI platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if hasattr(settings, 'ALLOWED_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection manager
manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Handle startup events."""
    logger.info("WebSocket service starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle shutdown events."""
    logger.info("WebSocket service shutting down...")
    await manager.disconnect_all()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "websocket"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time communication.

    Args:
        websocket: WebSocket connection
        user_id: User ID for the connection
    """
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle different event types
            event_type = data.get("type")

            if event_type == EventType.PING:
                # Respond to ping
                await manager.send_personal_message(
                    {"type": EventType.PONG, "data": {}},
                    user_id
                )
            else:
                # Echo back for now (can be extended with specific handlers)
                await manager.send_personal_message(data, user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for user {user_id}: {e}")
        manager.disconnect(user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
