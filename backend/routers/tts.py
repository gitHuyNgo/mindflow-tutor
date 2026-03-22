import logging

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from providers.openai_provider import get_openai_provider

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tts"])


@router.post("/v1/tts/stream")
async def stream_tts(text: str):
    """Stream TTS audio via OpenAI"""
    try:
        tts = get_openai_provider()

        async def generate():
            async for chunk in tts.generate_speech_stream(text):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="audio/mpeg",
            headers={"Transfer-Encoding": "chunked"},
        )
    except Exception as e:
        logger.error(f"TTS streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/tts/generate", response_model=dict)
async def generate_tts(text: str):
    """Generate TTS audio via OpenAI"""
    try:
        tts = get_openai_provider()
        audio_base64 = await tts.generate_speech_base64(text)
        return {"audio_base64": audio_base64, "text": text, "success": True}
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/stt", response_model=dict)
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio to text using OpenAI Whisper"""
    try:
        provider = get_openai_provider()
        audio_bytes = await audio.read()
        text = await provider.speech_to_text(audio_bytes, audio.filename or "audio.webm")
        return {"text": text, "success": True}
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
