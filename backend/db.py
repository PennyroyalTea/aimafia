"""MongoDB client singleton using motor (async driver)."""

from __future__ import annotations

import os

from motor.motor_asyncio import AsyncIOMotorClient


class _DatabaseProxy:
    """Proxy that forwards attribute access to the real database object.

    This avoids the Python import-rebinding problem: modules that do
    ``from backend.db import db`` get a reference to this proxy, which
    stays valid after ``init_db()`` sets the real database.
    """

    _db = None

    def __getattr__(self, name: str):
        if self._db is None:
            raise RuntimeError("Database not initialized -- call init_db() first")
        return getattr(self._db, name)


_client: AsyncIOMotorClient | None = None
db = _DatabaseProxy()


async def init_db() -> None:
    """Initialize the motor client and create indexes."""
    global _client
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/mafia")
    _client = AsyncIOMotorClient(mongo_url)
    db._db = _client["mafia"]
    await db.jobs.create_index([("video_url", 1), ("language", 1)])


async def close_db() -> None:
    """Close the motor client."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
