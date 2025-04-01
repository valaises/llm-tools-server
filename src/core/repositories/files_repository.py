import sqlite3
from datetime import datetime
from typing import List

from pydantic import BaseModel

from core.repositories.abstract_repository import AbstractRepository


class FileItem(BaseModel):
    file_name: str
    file_name_orig: str
    file_ext: str
    file_role: str # document etc.
    file_size: int
    user_id: int
    created_at: datetime
    file_type: str = ""
    processing_status: str = ""


class FilesRepository(AbstractRepository):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_db()

    def _init_db(self):
        with self._get_db_connection() as conn:
            # Check if columns exist
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
                file_type TEXT DEFAULT '',
                processing_status TEXT DEFAULT ''
            )
            """)

            # Add file_type column if it doesn't exist
            if 'file_type' not in columns and 'uploaded_files' in columns:
                conn.execute("ALTER TABLE uploaded_files ADD COLUMN file_type TEXT DEFAULT ''")

            # Add processing_status column if it doesn't exist
            if 'processing_status' not in columns and 'uploaded_files' in columns:
                conn.execute("ALTER TABLE uploaded_files ADD COLUMN processing_status TEXT DEFAULT ''")

            conn.commit()

    def create_file_sync(self, file: FileItem) -> bool:
        with self._get_db_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO uploaded_files 
                    (file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type, processing_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file.file_name,
                        file.file_name_orig,
                        file.file_ext,
                        file.file_role,
                        file.file_size,
                        file.user_id,
                        file.created_at.isoformat(),
                        file.file_type,
                        file.processing_status
                    )
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def update_file_sync(self, file_name: str, file: FileItem) -> bool:
        with self._get_db_connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    UPDATE uploaded_files
                    SET file_name_orig = ?, file_ext = ?, 
                        file_role = ?, file_size = ?, user_id = ?, created_at = ?, file_type = ?, processing_status = ?
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
                        file.processing_status,
                        file_name
                    )
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def delete_file_sync(self, file_name: str) -> bool:
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

    def get_user_files_sync(self, user_id: int) -> List[FileItem]:
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type, processing_status
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
                    file_type=row[7] if len(row) > 7 else "",
                    processing_status=row[8] if len(row) > 8 else ""
                ))

            return files

    def get_files_by_filter_sync(self, filter: str, params: tuple = ()) -> List[FileItem]:
        """
        Get files based on a custom filter expression.

        Args:
            filter: SQL WHERE clause (without the 'WHERE' keyword)
            params: Parameters to be used with the filter expression

        Returns:
            List of FileItem objects matching the filter
        """
        with self._get_db_connection() as conn:
            query = f"""
            SELECT file_name, file_name_orig, file_ext, file_role, file_size, user_id, created_at, file_type, processing_status
            FROM uploaded_files
            WHERE {filter}
            ORDER BY created_at DESC
            """
            cursor = conn.execute(query, params)

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
                    file_type=row[7] if len(row) > 7 else "",
                    processing_status=row[8] if len(row) > 8 else ""
                ))

            return files

    async def create_file(self, file: FileItem) -> bool:
        return await self._run_in_thread(self.create_file_sync, file)

    async def update_file(self, file_name: str, file: FileItem) -> bool:
        return await self._run_in_thread(self.update_file_sync, file_name, file)

    async def delete_file(self, file_name: str) -> bool:
        return await self._run_in_thread(self.delete_file_sync, file_name)

    async def get_user_files(self, user_id: int) -> List[FileItem]:
        return await self._run_in_thread(self.get_user_files_sync, user_id)

    async def get_files_by_filter(self, filter: str, params: tuple = ()) -> List[FileItem]:
        """
        Async version of get_files_by_filter_sync.

        Args:
            filter: SQL WHERE clause (without the 'WHERE' keyword)
            params: Parameters to be used with the filter expression

        Returns:
            List of FileItem objects matching the filter

        Examples:
            Get all PDF files:
            files = await repo.get_files_by_filter("file_ext = ?", ("pdf",))

            Get files with a specific processing status for a user:
            files = await repo.get_files_by_filter("user_id = ? AND processing_status = ?", (user_id, "completed"))
        """
        return await self._run_in_thread(self.get_files_by_filter_sync, filter, params)
