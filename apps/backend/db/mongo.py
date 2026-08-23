"""Async MongoDB client and collection operations using Motor."""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from apps.backend.config import settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def init_db() -> AsyncIOMotorDatabase:
    """Initialize MongoDB connection and create necessary indexes."""
    global _client, _db
    if _db is not None:
        return _db

    print(f"Connecting to MongoDB at {settings.mongo_uri}...")
    _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    _db = _client[settings.mongo_db_name]

    # Create indexes for fast querying
    await _db.sessions.create_index("last_active")
    await _db.messages.create_index([("session_id", 1), ("timestamp", 1)])
    await _db.documents.create_index("created_at")

    print(f"✅ Connected to MongoDB database: {settings.mongo_db_name}")
    return _db


async def close_db() -> None:
    """Close MongoDB connection pool."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """Return initialized database instance."""
    if _db is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return _db


# Helper CRUD functions for Sessions and Messages

async def create_session(title: str = "New Conversation", user_id: str = "default_user") -> dict[str, Any]:
    db = get_db()
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "_id": session_id,
        "session_id": session_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "last_active": now,
    }
    await db.sessions.insert_one(doc)
    return doc


async def get_sessions(user_id: str = "default_user", limit: int = 50) -> list[dict[str, Any]]:
    db = get_db()
    cursor = db.sessions.find({"user_id": user_id}).sort("last_active", -1).limit(limit)
    sessions = []
    async for s in cursor:
        sessions.append(s)
    return sessions


async def get_session(session_id: str) -> Optional[dict[str, Any]]:
    db = get_db()
    return await db.sessions.find_one({"session_id": session_id})


async def add_message(
    session_id: str,
    role: str,
    text: str,
    audio_url: Optional[str] = None,
) -> dict[str, Any]:
    db = get_db()
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    msg = {
        "_id": msg_id,
        "message_id": msg_id,
        "session_id": session_id,
        "role": role,
        "text": text,
        "timestamp": now,
        "audio_url": audio_url,
    }
    await db.messages.insert_one(msg)
    # Update session last_active
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"last_active": now}},
    )
    return msg


async def get_messages(session_id: str, limit: int = 100) -> list[dict[str, Any]]:
    db = get_db()
    cursor = db.messages.find({"session_id": session_id}).sort("timestamp", 1).limit(limit)
    messages = []
    async for m in cursor:
        messages.append(m)
    return messages


async def delete_session(session_id: str) -> bool:
    db = get_db()
    await db.messages.delete_many({"session_id": session_id})
    res = await db.sessions.delete_one({"session_id": session_id})
    return res.deleted_count > 0
