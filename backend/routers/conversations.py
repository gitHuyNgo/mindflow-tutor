import logging
from typing import List

from fastapi import APIRouter, HTTPException

from schemas.models import ConversationHistory, ConversationMessage
from persistence.session_memory import get_session_memory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["conversations"])


@router.get("/v1/conversations/{session_id}", response_model=ConversationHistory)
async def get_conversation(session_id: str):
    """Get conversation history"""
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
    """List all sessions"""
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
