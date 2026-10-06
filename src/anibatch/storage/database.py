from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


class Database:
    """Manages SQLite connection lifecycle, WAL mode, and transactions."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self.db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        try:
            yield db
        finally:
            await db.close()
