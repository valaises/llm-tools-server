import asyncio
import sqlite3

from functools import partial
from contextlib import contextmanager
from pathlib import Path


class AbstractRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    @contextmanager
    def _get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        raise NotImplementedError("Subclasses must implement this method")

    async def _run_in_thread(self, func, *args):
        """Run a blocking function in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args))
