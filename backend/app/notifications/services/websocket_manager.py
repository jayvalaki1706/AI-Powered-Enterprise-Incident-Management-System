import json
import logging
from fastapi import WebSocket
from uuid import UUID

logger = logging.getLogger("websocket")


class WebSocketManager:
    """
    Manages WebSocket connections for real-time notifications.
    Each user can have multiple connections (multiple tabs/devices).
    """

    def __init__(self):
        # user_id -> list of active WebSocket connections
        self.active_connections: dict[UUID, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user={user_id}, total_connections={self.get_connection_count()}")

    def disconnect(self, websocket: WebSocket, user_id: UUID):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}, total_connections={self.get_connection_count()}")

    async def send_to_user(self, user_id: UUID, message: dict):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[user_id].remove(conn)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast(self, message: dict):
        """Send a message to all connected users."""
        dead_users = []
        for user_id, connections in self.active_connections.items():
            dead_connections = []
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)

            for conn in dead_connections:
                connections.remove(conn)
            if not connections:
                dead_users.append(user_id)

        for user_id in dead_users:
            del self.active_connections[user_id]

    def is_user_online(self, user_id: UUID) -> bool:
        """Check if a user has any active connections."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_online_users(self) -> list[UUID]:
        """Get list of all online user IDs."""
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())


# Singleton instance - shared across the application
ws_manager = WebSocketManager()
