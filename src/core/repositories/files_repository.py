import sqlite3
from datetime import datetime
from typing import List

from pydantic import BaseModel

from core.repositories.abstract_repository import AbstractRepository


class FileItem(BaseModel):
    file_name: str
    file_name_orig: str
    file_ext: str
    file_role: str
    file_size: int
    user_id: int
    created_at: datetime
    file_type: str = ""


class FilesRepository(AbstractRepository):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_db()

    def _init_db(self):
        with self._get_db_connection() as conn:
            # Check if file_type column exists
            cursor = conn.execute("PRAGMA table_info(uploaded_files)")
            columns = [info[1] for info in cursor.fetchall()]

            # Create table if it doesn't exist
            conn.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                file_name TEXT PRIMARY KEY,
                file_name_orig TEXT NOT NULL,
                file_ext TEXT NOT NULL,
                file_role TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                file_type TEXT DEFAULT ''
            )
            """)

            # Add file_type column if it doesn't exist
            if 'file_type' not in columns and 'uploaded_files' in columns:
                conn.execute("ALTER TABLE uploaded_files ADD COLUMN file_type TEXT DEFAULT ''")

            conn.commit()

    def _create_file_sync(self, file: FileItem) -> bool:
        with self._get_db_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO uploaded_files 
                    (file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file.file_name,
                        file.file_name_orig,
                        file.file_ext,
                        file.file_role,
                        file.file_size,
                        file.user_id,
                        file.created_at.isoformat(),
                        file.file_type
                    )
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def _update_file_sync(self, file_name: str, file: FileItem) -> bool:
        with self._get_db_connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    UPDATE uploaded_files
                    SET file_name_orig = ?, file_ext = ?, 
                        file_role = ?, file_size = ?, user_id = ?, created_at = ?, file_type = ?
                    WHERE file_name = ?
                    """,
                    (
                        file.file_name_orig,
                        file.file_ext,
                        file.file_role,
                        file.file_size,
                        file.user_id,
                        file.created_at.isoformat(),
                        file.file_type,
                        file_name
                    )
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def _delete_file_sync(self, file_name: str) -> bool:
        with self._get_db_connection() as conn:
            try:
                cursor = conn.execute(
                    "DELETE FROM uploaded_files WHERE file_name = ?",
                    (file_name,)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def _get_user_files_sync(self, user_id: int) -> List[FileItem]:
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type
                FROM uploaded_files
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )

            files = []
            for row in cursor.fetchall():
                files.append(FileItem(
                    file_name=row[0],
                    file_name_orig=row[1],
                    file_ext=row[2],
                    file_role=row[3],
                    file_size=row[4],
                    user_id=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    file_type=row[7] if len(row) > 7 else ""
                ))

            return files

    def _get_file_by_name_sync(self, file_name: str) -> FileItem | None:
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type
                FROM uploaded_files
                WHERE file_name = ?
                """,
                (file_name,)
            )

            row = cursor.fetchone()
            if row:
                return FileItem(
                    file_name=row[0],
                    file_name_orig=row[1],
                    file_ext=row[2],
                    file_role=row[3],
                    file_size=row[4],
                    user_id=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    file_type=row[7] if len(row) > 7 else ""
                )
            return None

    def _get_all_files_sync(self) -> List[FileItem]:
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type
                FROM uploaded_files
                ORDER BY created_at DESC
                """
            )

            files = []
            for row in cursor.fetchall():
                files.append(FileItem(
                    file_name=row[0],
                    file_name_orig=row[1],
                    file_ext=row[2],
                    file_role=row[3],
                    file_size=row[4],
                    user_id=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    file_type=row[7] if len(row) > 7 else ""
                ))

            return files

    async def create_file(self, file: FileItem) -> bool:
        return await self._run_in_thread(self._create_file_sync, file)

    async def update_file(self, file_name: str, file: FileItem) -> bool:
        return await self._run_in_thread(self._update_file_sync, file_name, file)

    async def delete_file(self, file_name: str) -> bool:
        return await self._run_in_thread(self._delete_file_sync, file_name)

    async def get_user_files(self, user_id: int) -> List[FileItem]:
        return await self._run_in_thread(self._get_user_files_sync, user_id)

    async def get_file_by_name(self, file_name: str) -> FileItem | None:
        return await self._run_in_thread(self._get_file_by_name_sync, file_name)

    async def get_all_files(self) -> List[FileItem]:
        return await self._run_in_thread(self._get_all_files_sync)
