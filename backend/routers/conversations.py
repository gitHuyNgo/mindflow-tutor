import logging
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from schemas.models import ConversationHistory, ConversationMessage
from persistence.session_memory import get_session_memory
from core.database import get_db
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["conversations"])


class SessionMetadata(BaseModel):
    session_id: str
    title: str = "Study Session"
    subject: str = ""


@router.post("/v1/sessions")
async def save_session_metadata(
    meta: SessionMetadata,
    current_user: dict = Depends(get_current_user),
):
    """Save or update session title/subject in MongoDB for the authenticated user."""
    try:
        db = get_db()
        user_id = current_user["id"]
        from datetime import datetime, timezone

        # Verify existing session ownership: default-deny if session exists and is unowned or belongs to another user
        existing = await db.conversations.find_one({"session_id": meta.session_id})
        if existing:
            existing_owner = existing.get("user_id")
            if not existing_owner or existing_owner != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to modify this session")
        await db.conversations.update_one(
            {"session_id": meta.session_id},
            {
                "$set": {
                    "user_id": user_id,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving session metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/sessions")
async def list_sessions_mongo(
    current_user: dict = Depends(get_current_user),
):
    """List sessions from MongoDB owned by the authenticated user (most recent first)."""
    try:
        db = get_db()
        user_id = current_user["id"]
        cursor = db.conversations.find(
            {"user_id": user_id},
            {"_id": 0, "session_id": 1, "title": 1, "subject": 1, "created_at": 1, "updated_at": 1}
        ).sort("updated_at", -1).limit(50)
        docs = await cursor.to_list(length=50)
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
async def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get saved conversation messages for a session owned by the authenticated user from MongoDB."""
    try:
        db = get_db()
        user_id = current_user["id"]
        doc = await db.conversations.find_one(
            {"session_id": session_id},
            {"_id": 0, "user_id": 1, "messages": 1}
        )
        if not doc:
            return {"session_id": session_id, "messages": []}
        doc_owner = doc.get("user_id")
        if not doc_owner or doc_owner != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        return {"session_id": session_id, "messages": doc.get("messages", [])}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/conversations/{session_id}", response_model=ConversationHistory)
async def get_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get conversation history (in-memory/persistence) for the authenticated user."""
    try:
        memory = get_session_memory()
        user_id = current_user["id"]
        has_access = await memory.check_session_access_async(session_id, user_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
        messages = await memory.get_history_async(session_id)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/conversations", response_model=List[dict])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
):
    """List all sessions for the authenticated user."""
    try:
        memory = get_session_memory()
        return await memory.get_all_sessions_async(user_id=current_user["id"])
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/v1/conversations/{session_id}")
async def clear_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Clear conversation owned by the authenticated user."""
    try:
        memory = get_session_memory()
        user_id = current_user["id"]
        has_access = await memory.check_session_access_async(session_id, user_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Not authorized to clear this conversation")
        await memory.clear_session_async(session_id)
        return {"status": "cleared", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
