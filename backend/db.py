"""MongoDB client singleton using motor (async driver)."""

from __future__ import annotations

import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase = None  # type: ignore[assignment]


async def init_db() -> None:
    """Initialize the motor client and create indexes."""
    global _client, db
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/mafia")
    _client = AsyncIOMotorClient(mongo_url)
    db = _client["mafia"]
    await db.jobs.create_index([("video_url", 1), ("language", 1)])


async def close_db() -> None:
    """Close the motor client."""
    global _client, db
    if _client is not None:
        _client.close()
        _client = None
