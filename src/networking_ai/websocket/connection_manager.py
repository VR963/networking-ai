"""
WebSocket Connection Manager - Phase 3 Week 1.

Manages WebSocket connections for real-time features.

Key Features:
- Connection lifecycle management (connect/disconnect/heartbeat)
- User/agent connection tracking
- Broadcasting to specific users or agent types
- Connection pooling and cleanup
- Presence tracking (online/offline/away)
- Rate limiting and connection limits
"""

from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from enum import Enum


class PresenceStatus(str, Enum):
    """User presence status."""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class ConnectionInfo:
    """Information about a WebSocket connection."""

    def __init__(
        self,
        websocket: WebSocket,
        user_id: int,
        agent_type: Optional[str] = None,
        agent_id: Optional[int] = None
    ):
        """
        Initialize connection info.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            agent_type: Agent type (talent/hiring_manager/company_admin)
            agent_id: Agent ID
        """
        self.websocket = websocket
        self.user_id = user_id
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.presence = PresenceStatus.ONLINE
        self.connection_id = f"{user_id}_{datetime.utcnow().timestamp()}"

    def update_heartbeat(self):
        """Update last heartbeat time."""
        self.last_heartbeat = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.presence = PresenceStatus.ONLINE

    def update_activity(self):
        """Update last activity time."""
        self.last_activity = datetime.utcnow()
        if self.presence == PresenceStatus.AWAY:
            self.presence = PresenceStatus.ONLINE

    def mark_away(self):
        """Mark connection as away."""
        self.presence = PresenceStatus.AWAY

    def mark_offline(self):
        """Mark connection as offline."""
        self.presence = PresenceStatus.OFFLINE

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """
        Check if connection is stale (no heartbeat).

        Args:
            timeout_seconds: Timeout in seconds (default 5 minutes)

        Returns:
            True if stale
        """
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() > timeout_seconds

    def should_mark_away(self, away_threshold_seconds: int = 60) -> bool:
        """
        Check if connection should be marked as away.

        Args:
            away_threshold_seconds: Threshold in seconds (default 1 minute)

        Returns:
            True if should be marked away
        """
        if self.presence == PresenceStatus.AWAY:
            return False
        return (datetime.utcnow() - self.last_activity).total_seconds() > away_threshold_seconds

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "presence": self.presence.value,
            "duration_seconds": (datetime.utcnow() - self.connected_at).total_seconds()
        }


class ConnectionManager:
    """
    Manages WebSocket connections for real-time features.

    Handles connection lifecycle, broadcasting, presence tracking.
    """

    def __init__(
        self,
        max_connections_per_user: int = 5,
        heartbeat_timeout: int = 300,
        away_threshold: int = 60
    ):
        """
        Initialize connection manager.

        Args:
            max_connections_per_user: Maximum connections per user
            heartbeat_timeout: Heartbeat timeout in seconds
            away_threshold: Away threshold in seconds
        """
        # WebSocket connections by connection_id
        self._connections: Dict[str, ConnectionInfo] = {}

        # User ID -> Set of connection_ids
        self._user_connections: Dict[int, Set[str]] = {}

        # Agent -> Set of connection_ids
        self._agent_connections: Dict[str, Set[str]] = {}  # Key: "agent_type:agent_id"

        # Configuration
        self.max_connections_per_user = max_connections_per_user
        self.heartbeat_timeout = heartbeat_timeout
        self.away_threshold = away_threshold

        # Statistics
        self._stats = {
            "total_connections": 0,
            "total_disconnections": 0,
            "messages_sent": 0,
            "broadcasts": 0
        }

        # Start background tasks
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        agent_type: Optional[str] = None,
        agent_id: Optional[int] = None
    ) -> str:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            agent_type: Optional agent type
            agent_id: Optional agent ID

        Returns:
            Connection ID

        Raises:
            Exception if max connections exceeded
        """
        # Check connection limit
        if user_id in self._user_connections:
            if len(self._user_connections[user_id]) >= self.max_connections_per_user:
                raise Exception(f"Max connections ({self.max_connections_per_user}) exceeded for user {user_id}")

        # Accept connection
        await websocket.accept()

        # Create connection info
        conn_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            agent_type=agent_type,
            agent_id=agent_id
        )

        # Register connection
        self._connections[conn_info.connection_id] = conn_info

        # Track by user
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(conn_info.connection_id)

        # Track by agent
        if agent_type and agent_id:
            agent_key = f"{agent_type}:{agent_id}"
            if agent_key not in self._agent_connections:
                self._agent_connections[agent_key] = set()
            self._agent_connections[agent_key].add(conn_info.connection_id)

        # Update stats
        self._stats["total_connections"] += 1

        print(f"[WebSocket] Connected: {conn_info.connection_id} (user={user_id}, agent={agent_type}:{agent_id})")

        return conn_info.connection_id

    async def disconnect(self, connection_id: str):
        """
        Disconnect and unregister a WebSocket connection.

        Args:
            connection_id: Connection ID to disconnect
        """
        if connection_id not in self._connections:
            return

        conn_info = self._connections[connection_id]
        conn_info.mark_offline()

        # Remove from tracking
        user_id = conn_info.user_id
        if user_id in self._user_connections:
            self._user_connections[user_id].discard(connection_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

        # Remove from agent tracking
        if conn_info.agent_type and conn_info.agent_id:
            agent_key = f"{conn_info.agent_type}:{conn_info.agent_id}"
            if agent_key in self._agent_connections:
                self._agent_connections[agent_key].discard(connection_id)
                if not self._agent_connections[agent_key]:
                    del self._agent_connections[agent_key]

        # Remove connection
        del self._connections[connection_id]

        # Update stats
        self._stats["total_disconnections"] += 1

        print(f"[WebSocket] Disconnected: {connection_id}")

    async def send_personal_message(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ):
        """
        Send a message to a specific connection.

        Args:
            connection_id: Connection ID
            message: Message dictionary
        """
        if connection_id not in self._connections:
            return

        conn_info = self._connections[connection_id]

        try:
            await conn_info.websocket.send_json(message)
            conn_info.update_activity()
            self._stats["messages_sent"] += 1
        except Exception as e:
            print(f"[WebSocket] Failed to send to {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def send_to_user(
        self,
        user_id: int,
        message: Dict[str, Any]
    ):
        """
        Send a message to all connections of a user.

        Args:
            user_id: User ID
            message: Message dictionary
        """
        if user_id not in self._user_connections:
            return

        connection_ids = list(self._user_connections[user_id])
        for connection_id in connection_ids:
            await self.send_personal_message(connection_id, message)

    async def send_to_agent(
        self,
        agent_type: str,
        agent_id: int,
        message: Dict[str, Any]
    ):
        """
        Send a message to all connections of an agent.

        Args:
            agent_type: Agent type
            agent_id: Agent ID
            message: Message dictionary
        """
        agent_key = f"{agent_type}:{agent_id}"
        if agent_key not in self._agent_connections:
            return

        connection_ids = list(self._agent_connections[agent_key])
        for connection_id in connection_ids:
            await self.send_personal_message(connection_id, message)

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connections.

        Args:
            message: Message dictionary
        """
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.send_personal_message(connection_id, message)

        self._stats["broadcasts"] += 1

    async def broadcast_to_agent_type(
        self,
        agent_type: str,
        message: Dict[str, Any]
    ):
        """
        Broadcast to all connections of a specific agent type.

        Args:
            agent_type: Agent type (talent/hiring_manager/company_admin)
            message: Message dictionary
        """
        # Find all agents of this type
        matching_agents = [
            key for key in self._agent_connections.keys()
            if key.startswith(f"{agent_type}:")
        ]

        for agent_key in matching_agents:
            connection_ids = list(self._agent_connections[agent_key])
            for connection_id in connection_ids:
                await self.send_personal_message(connection_id, message)

        self._stats["broadcasts"] += 1

    def get_user_presence(self, user_id: int) -> PresenceStatus:
        """
        Get presence status for a user.

        Args:
            user_id: User ID

        Returns:
            Presence status (ONLINE if any connection is online)
        """
        if user_id not in self._user_connections:
            return PresenceStatus.OFFLINE

        # Check all user connections
        for connection_id in self._user_connections[user_id]:
            if connection_id in self._connections:
                conn_info = self._connections[connection_id]
                if conn_info.presence == PresenceStatus.ONLINE:
                    return PresenceStatus.ONLINE

        # Check if any are away
        for connection_id in self._user_connections[user_id]:
            if connection_id in self._connections:
                conn_info = self._connections[connection_id]
                if conn_info.presence == PresenceStatus.AWAY:
                    return PresenceStatus.AWAY

        return PresenceStatus.OFFLINE

    def is_user_online(self, user_id: int) -> bool:
        """Check if a user is online."""
        return self.get_user_presence(user_id) == PresenceStatus.ONLINE

    def get_online_users(self) -> List[int]:
        """Get list of all online user IDs."""
        return list(self._user_connections.keys())

    def get_connection_info(self, connection_id: str) -> Optional[Dict]:
        """Get connection info dictionary."""
        if connection_id not in self._connections:
            return None
        return self._connections[connection_id].to_dict()

    def get_user_connections(self, user_id: int) -> List[Dict]:
        """Get all connection info for a user."""
        if user_id not in self._user_connections:
            return []

        connections = []
        for connection_id in self._user_connections[user_id]:
            if connection_id in self._connections:
                connections.append(self._connections[connection_id].to_dict())

        return connections

    def get_stats(self) -> Dict:
        """Get connection manager statistics."""
        return {
            **self._stats,
            "active_connections": len(self._connections),
            "active_users": len(self._user_connections),
            "active_agents": len(self._agent_connections)
        }

    async def cleanup_stale_connections(self):
        """Clean up stale connections (no heartbeat)."""
        stale_connections = []

        for connection_id, conn_info in self._connections.items():
            if conn_info.is_stale(self.heartbeat_timeout):
                stale_connections.append(connection_id)
            elif conn_info.should_mark_away(self.away_threshold):
                conn_info.mark_away()

        # Disconnect stale connections
        for connection_id in stale_connections:
            print(f"[WebSocket] Cleaning up stale connection: {connection_id}")
            await self.disconnect(connection_id)

        if stale_connections:
            print(f"[WebSocket] Cleaned up {len(stale_connections)} stale connections")

    async def start_background_tasks(self):
        """Start background tasks (cleanup, etc.)."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._background_cleanup())

    async def _background_cleanup(self):
        """Background task for periodic cleanup."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self.cleanup_stale_connections()
            except Exception as e:
                print(f"[WebSocket] Background cleanup error: {e}")

    async def stop_background_tasks(self):
        """Stop background tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get or create global connection manager instance.

    Returns:
        ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
