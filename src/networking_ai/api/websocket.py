"""
WebSocket API Routes - Phase 3 Week 1.

Real-time WebSocket endpoints for live updates.

Endpoints:
- /ws - WebSocket connection endpoint
- /ws/stats - Connection statistics (HTTP GET)
- /ws/presence/{user_id} - Get user presence (HTTP GET)
"""

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session
import asyncio
import json

from ..database import get_db
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentType
from ..api.auth import get_current_active_user
from ..websocket.connection_manager import get_connection_manager, PresenceStatus
from ..websocket.event_types import (
    ConnectedEvent,
    HeartbeatResponse,
    ErrorEvent,
    TypingEvent,
    MessageReadEvent,
    PresenceEvent,
    ClientMessage
)


router = APIRouter(prefix="/ws", tags=["WebSocket"])


# ==================== WebSocket Connection Endpoint ====================

@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket connection endpoint.

    Handles:
    - Connection authentication
    - Heartbeat monitoring
    - Event routing
    - Graceful disconnection

    Query Parameters:
    - token: JWT authentication token

    Client Message Format:
    {
        "action": "heartbeat|typing|mark_read|update_presence",
        "data": {...}
    }

    Server Event Format:
    {
        "event": "event.type",
        "timestamp": "2024-01-01T00:00:00",
        "data": {...}
    }
    """
    connection_manager = get_connection_manager()
    connection_id: Optional[str] = None

    try:
        # Authenticate user from token
        # NOTE: In production, implement proper JWT token validation here
        # For now, we'll use a simple user_id extraction from token
        user = await authenticate_websocket(token, db)

        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Get user's agent (prefer talent, then HM, then company admin)
        agent_type, agent_id = await get_user_agent(user.id, db)

        # Connect
        connection_id = await connection_manager.connect(
            websocket=websocket,
            user_id=user.id,
            agent_type=agent_type,
            agent_id=agent_id
        )

        # Send connected event
        connected_event = ConnectedEvent.create(
            connection_id=connection_id,
            user_id=user.id
        )
        await websocket.send_json(connected_event.dict())

        # Broadcast presence online
        if agent_type and agent_id:
            presence_event = PresenceEvent.create(
                user_id=user.id,
                presence_status="online",
                agent_type=agent_type,
                agent_id=agent_id
            )
            # Broadcast to relevant users (e.g., conversation partners)
            # For now, we'll skip broadcasting to save complexity

        # Message loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                client_message = ClientMessage(**message)

                # Route action
                await handle_client_action(
                    connection_id=connection_id,
                    user_id=user.id,
                    agent_type=agent_type,
                    agent_id=agent_id,
                    action=client_message.action,
                    data=client_message.data,
                    connection_manager=connection_manager,
                    db=db
                )

            except json.JSONDecodeError:
                error_event = ErrorEvent.create("Invalid JSON format")
                await websocket.send_json(error_event.dict())

            except Exception as e:
                error_event = ErrorEvent.create(str(e), error_code="ACTION_ERROR")
                await websocket.send_json(error_event.dict())

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: {connection_id}")

    except Exception as e:
        print(f"[WebSocket] Error: {e}")

    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id)

            # Broadcast presence offline
            if 'user' in locals() and 'agent_type' in locals() and 'agent_id' in locals():
                presence_event = PresenceEvent.create(
                    user_id=user.id,
                    presence_status="offline",
                    agent_type=agent_type,
                    agent_id=agent_id
                )
                # Broadcast to relevant users


# ==================== Helper Functions ====================

async def authenticate_websocket(token: str, db: Session) -> Optional[User]:
    """
    Authenticate WebSocket connection using token.

    Args:
        token: Authentication token
        db: Database session

    Returns:
        User if authenticated, None otherwise
    """
    # TODO: Implement proper JWT token validation
    # For now, we'll do a simple user_id extraction

    # Placeholder: Extract user_id from token
    # In production, this would be:
    # 1. Decode JWT token
    # 2. Verify signature
    # 3. Check expiration
    # 4. Get user from token payload

    try:
        # Simple implementation: token is just user_id for testing
        if token.startswith("user_"):
            user_id = int(token.split("_")[1])
            user = db.query(User).filter(User.id == user_id).first()
            return user
    except:
        pass

    return None


async def get_user_agent(user_id: int, db: Session) -> tuple[Optional[str], Optional[int]]:
    """
    Get user's primary agent.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Tuple of (agent_type, agent_id)
    """
    # Try talent agent first
    talent_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == user_id,
        PersonalAIAgent.agent_type == AgentType.TALENT
    ).first()

    if talent_agent:
        return ("talent", talent_agent.id)

    # Try HM agent
    hm_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == user_id,
        PersonalAIAgent.agent_type == AgentType.HIRING_MANAGER
    ).first()

    if hm_agent:
        return ("hiring_manager", hm_agent.id)

    # Try Company Admin agent
    from ..models.company_admin_agent import CompanyAdminAgent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.created_by_user_id == user_id
    ).first()

    if admin_agent:
        return ("company_admin", admin_agent.id)

    return (None, None)


async def handle_client_action(
    connection_id: str,
    user_id: int,
    agent_type: Optional[str],
    agent_id: Optional[int],
    action: str,
    data: dict,
    connection_manager,
    db: Session
):
    """
    Handle client action/message.

    Args:
        connection_id: Connection ID
        user_id: User ID
        agent_type: Agent type
        agent_id: Agent ID
        action: Action type
        data: Action data
        connection_manager: Connection manager
        db: Database session
    """
    if action == "heartbeat":
        # Send heartbeat response
        response = HeartbeatResponse.create()
        await connection_manager.send_personal_message(connection_id, response.dict())

    elif action == "typing":
        # Broadcast typing indicator
        thread_id = data.get("thread_id")
        typing_status = data.get("status", "start")  # start or stop

        if thread_id and agent_type and agent_id:
            if typing_status == "start":
                event = TypingEvent.create_start(
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_type=agent_type,
                    agent_id=agent_id
                )
            else:
                event = TypingEvent.create_stop(
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_type=agent_type,
                    agent_id=agent_id
                )

            # Broadcast to conversation partners
            # TODO: Get conversation partners from thread_id and broadcast
            # For now, we'll skip this

    elif action == "mark_read":
        # Mark message(s) as read
        message_id = data.get("message_id")
        thread_id = data.get("thread_id")

        if message_id:
            # Mark single message as read
            from ..models.agent_message import AgentMessage
            from datetime import datetime

            message = db.query(AgentMessage).filter(
                AgentMessage.id == message_id,
                AgentMessage.receiver_agent_type == agent_type,
                AgentMessage.receiver_agent_id == agent_id
            ).first()

            if message:
                message.mark_read()
                db.commit()

                # Send confirmation
                event = MessageReadEvent.create(
                    message_id=message_id,
                    thread_id=message.thread_id,
                    read_by_user_id=user_id,
                    read_at=datetime.utcnow().isoformat()
                )
                await connection_manager.send_personal_message(connection_id, event.dict())

    elif action == "update_presence":
        # Update presence status
        presence_status = data.get("status", "online")

        presence_event = PresenceEvent.create(
            user_id=user_id,
            presence_status=presence_status,
            agent_type=agent_type,
            agent_id=agent_id
        )

        # Send confirmation
        await connection_manager.send_personal_message(connection_id, presence_event.dict())

    else:
        # Unknown action
        error_event = ErrorEvent.create(
            f"Unknown action: {action}",
            error_code="UNKNOWN_ACTION"
        )
        await connection_manager.send_personal_message(connection_id, error_event.dict())


# ==================== HTTP Endpoints for WebSocket Info ====================

@router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns connection counts, online users, etc.
    """
    connection_manager = get_connection_manager()
    stats = connection_manager.get_stats()

    return {
        "status": "ok",
        "stats": stats
    }


@router.get("/presence/{user_id}")
async def get_user_presence(
    user_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get presence status for a specific user.

    Args:
        user_id: User ID to check

    Returns:
        Presence status (online/away/offline)
    """
    connection_manager = get_connection_manager()
    presence = connection_manager.get_user_presence(user_id)

    return {
        "user_id": user_id,
        "presence": presence.value,
        "is_online": presence == PresenceStatus.ONLINE
    }


@router.get("/online-users")
async def get_online_users(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all online user IDs.

    Requires authentication.
    """
    connection_manager = get_connection_manager()
    online_users = connection_manager.get_online_users()

    return {
        "online_users": online_users,
        "count": len(online_users)
    }


@router.post("/start")
async def start_websocket_background_tasks():
    """
    Start WebSocket background tasks (cleanup, etc.).

    Should be called on application startup.
    """
    connection_manager = get_connection_manager()
    await connection_manager.start_background_tasks()

    return {
        "status": "started",
        "message": "WebSocket background tasks started"
    }


@router.post("/stop")
async def stop_websocket_background_tasks():
    """
    Stop WebSocket background tasks.

    Should be called on application shutdown.
    """
    connection_manager = get_connection_manager()
    await connection_manager.stop_background_tasks()

    return {
        "status": "stopped",
        "message": "WebSocket background tasks stopped"
    }
