import sqlite3
from datetime import datetime
from typing import List

from pydantic import BaseModel

from core.repositories.abstract_repository import AbstractRepository


class MCPLServer(BaseModel):
    id: int = None
    user_id: int
    address: str
    is_active: bool


class MCPLServersRepository(AbstractRepository):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_db()

    def _init_db(self):
        with self._get_db_connection() as conn:
            # Create table if it doesn't exist
            conn.execute("""
            CREATE TABLE IF NOT EXISTS mcpl_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                is_active BOOLEAN NOT NULL
            )
            """)
            conn.commit()

    def create_server_sync(self, server: MCPLServer) -> int:
        with self._get_db_connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO mcpl_servers 
                    (user_id, address, is_active)
                    VALUES (?, ?, ?)
                    """,
                    (
                        server.user_id,
                        server.address,
                        server.is_active
                    )
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error:
                return None

    def update_server_sync(self, server: MCPLServer) -> bool:
        with self._get_db_connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    UPDATE mcpl_servers
                    SET user_id = ?, address = ?, is_active = ?
                    WHERE id = ?
                    """,
                    (
                        server.user_id,
                        server.address,
                        server.is_active,
                        server.id
                    )
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def delete_server_sync(self, server_id: int) -> bool:
        with self._get_db_connection() as conn:
            try:
                cursor = conn.execute(
                    "DELETE FROM mcpl_servers WHERE id = ?",
                    (server_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def get_user_servers_sync(self, user_id: int) -> List[MCPLServer]:
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, user_id, address, is_active
                FROM mcpl_servers
                WHERE user_id = ?
                """,
                (user_id,)
            )

            servers = []
            for row in cursor.fetchall():
                servers.append(MCPLServer(
                    id=row[0],
                    user_id=row[1],
                    address=row[2],
                    is_active=row[3]
                ))

            return servers

    def update_user_servers_sync(self, user_id: int, servers: List[MCPLServer]) -> bool:
        with self._get_db_connection() as conn:
            try:
                # Start a transaction
                conn.execute("BEGIN TRANSACTION")

                # Delete all existing servers for the user
                conn.execute(
                    "DELETE FROM mcpl_servers WHERE user_id = ?",
                    (user_id,)
                )

                # Insert the new servers
                for server in servers:
                    conn.execute(
                        """
                        INSERT INTO mcpl_servers 
                        (user_id, address, is_active)
                        VALUES (?, ?, ?)
                        """,
                        (
                            user_id,
                            server.address,
                            server.is_active
                        )
                    )

                # Commit the transaction
                conn.commit()
                return True
            except sqlite3.Error:
                # Rollback in case of error
                conn.rollback()
                return False

    async def create_server(self, server: MCPLServer) -> int:
        return await self._run_in_thread(self.create_server_sync, server)

    async def update_server(self, server: MCPLServer) -> bool:
        return await self._run_in_thread(self.update_server_sync, server)

    async def delete_server(self, server_id: int) -> bool:
        return await self._run_in_thread(self.delete_server_sync, server_id)

    async def get_user_servers(self, user_id: int) -> List[MCPLServer]:
        return await self._run_in_thread(self.get_user_servers_sync, user_id)

    async def update_user_servers(self, user_id: int, servers: List[MCPLServer]) -> bool:
        """
        Replace all servers for a user with the provided list of servers.

        Args:
            user_id: The ID of the user whose servers are being updated
            servers: List of MCPLServer objects to replace the user's existing servers

        Returns:
            True if the operation was successful, False otherwise
        """
        return await self._run_in_thread(self.update_user_servers_sync, user_id, servers)
