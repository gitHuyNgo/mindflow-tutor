import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemas.models import ConversationHistory, ConversationMessage
from persistence.session_memory import get_session_memory
from core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["conversations"])


class SessionMetadata(BaseModel):
    session_id: str
    title: str = "Study Session"
    subject: str = ""


@router.post("/v1/sessions")
async def save_session_metadata(meta: SessionMetadata):
    """Save or update session title/subject in MongoDB."""
    try:
        db = get_db()
        from datetime import datetime, timezone
        await db.conversations.update_one(
            {"session_id": meta.session_id},
            {
                "$set": {
                    "title": meta.title,
                    "subject": meta.subject,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$setOnInsert": {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "messages": [],
                },
            },
            upsert=True,
        )
        return {"status": "ok", "session_id": meta.session_id}
    except Exception as e:
        logger.error(f"Error saving session metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/sessions")
async def list_sessions_mongo():
    """List sessions from MongoDB (most recent first)."""
    try:
        db = get_db()
        cursor = db.conversations.find(
            {},
            {"_id": 0, "session_id": 1, "title": 1, "subject": 1, "created_at": 1, "updated_at": 1,
             "message_count": {"$size": {"$ifNull": ["$messages", []]}}}
        ).sort("updated_at", -1).limit(50)
        docs = await cursor.to_list(length=50)
        # compute message_count manually since $size in projection requires MongoDB 4.4+
        result = []
        for d in docs:
            result.append({
                "session_id": d.get("session_id"),
                "title": d.get("title", "Study Session"),
                "subject": d.get("subject", ""),
                "created_at": d.get("created_at", ""),
                "updated_at": d.get("updated_at", ""),
            })
        return result
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get saved conversation messages for a session from MongoDB."""
    try:
        db = get_db()
        doc = await db.conversations.find_one(
            {"session_id": session_id},
            {"_id": 0, "messages": 1}
        )
        if not doc:
            return {"session_id": session_id, "messages": []}
        return {"session_id": session_id, "messages": doc.get("messages", [])}
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/conversations/{session_id}", response_model=ConversationHistory)
async def get_conversation(session_id: str):
    """Get conversation history (in-memory)"""
    try:
        memory = get_session_memory()
        messages = memory.get_history(session_id)
        return ConversationHistory(
            session_id=session_id,
            messages=[
                ConversationMessage(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg.get("timestamp", ""),
                    audio_url=msg.get("audio_url")
                )
                for msg in messages
            ]
        )
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/conversations", response_model=List[dict])
async def list_sessions():
    """List all in-memory sessions"""
    try:
        memory = get_session_memory()
        return memory.get_all_sessions()
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/v1/conversations/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation"""
    try:
        memory = get_session_memory()
        memory.clear_session(session_id)
        return {"status": "cleared", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
