import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from schemas.models import ProcessTriggerRequest, DetectorFrameRequest
from engines.orchestrator import get_orchestrator
from engines.combined_detector_engine import get_combined_detector_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai"])


@router.post("/v1/process-trigger", response_model=dict)
async def process_trigger(request: ProcessTriggerRequest):
    """Process confusion trigger with screen capture"""
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.process_confusion_trigger(
            screen_capture=request.screen_capture,
            session_id=request.session_id,
            user_query=request.user_query,
            use_web_search=True
        )
        return {
            "session_id": result["session_id"],
            "text_response": result["text_response"],
            "audio_base64": result.get("audio_base64"),
            "screen_analysis": result.get("screen_analysis"),
            "sources_used": result.get("sources_used", []),
            "success": result.get("success", True)
        }
    except Exception as e:
        logger.error(f"Error in process-trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/ask", response_model=dict)
async def ask_question(question: str, session_id: Optional[str] = None):
    """Direct question endpoint"""
    try:
        if not session_id:
            session_id = str(uuid.uuid4())

        orchestrator = get_orchestrator()
        result = await orchestrator.process_direct_question(
            question=question,
            session_id=session_id
        )
        return {
            "session_id": result["session_id"],
            "text_response": result["text_response"],
            "audio_base64": result.get("audio_base64"),
            "sources_used": result.get("sources_used", []),
            "success": result.get("success", True)
        }
    except Exception as e:
        logger.error(f"Error in ask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/detector/frame", response_model=dict)
async def detect_frame(request: DetectorFrameRequest):
    """Analyze one camera frame and return distraction/confusion states"""
    try:
        detector = get_combined_detector_engine()
        result = detector.detect_from_base64(request.image_base64)
        return result
    except Exception as e:
        logger.error(f"Error in detector/frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))
