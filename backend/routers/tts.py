import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from providers.elevenlabs_provider import get_elevenlabs_provider

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tts"])


@router.post("/v1/tts/stream")
async def stream_tts(text: str):
    """Stream TTS audio"""
    try:
        tts = get_elevenlabs_provider()

        def generate():
            for chunk in tts.generate_speech_stream(text):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="audio/mpeg",
            headers={"Transfer-Encoding": "chunked"}
        )
    except Exception as e:
        logger.error(f"TTS streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/tts/generate", response_model=dict)
async def generate_tts(text: str):
    """Generate TTS audio"""
    try:
        tts = get_elevenlabs_provider()
        audio_base64 = tts.generate_speech_base64(text)
        return {
            "audio_base64": audio_base64,
            "text": text,
            "success": True
        }
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
