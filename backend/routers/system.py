import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from schemas.models import SystemStatus
from engines.rag_retriever import get_rag_retriever
from persistence.session_memory import get_session_memory
from core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/")
async def root():
    return {"message": "MindFlow Tutor API", "version": "2.0.0", "voice_enabled": True}


@router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/v1/agora/config")
async def get_agora_config():
    """Get Agora configuration for client"""
    return {
        "app_id": os.environ.get("AGORA_APP_ID"),
        "channel": "mindflow-voice"
    }


@router.get("/v1/status", response_model=SystemStatus)
async def get_status():
    """Get system status"""
    try:
        memory = get_session_memory()
        db = get_db()
        doc_count = await db.documents.count_documents({})

        return SystemStatus(
            rag_ready=True,
            documents_indexed=doc_count,
            active_sessions=memory.get_active_sessions(),
            last_activity=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        return SystemStatus(
            rag_ready=False,
            documents_indexed=0,
            active_sessions=0
        )
