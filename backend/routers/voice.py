import json
import base64
import uuid
import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engines.audio_processor import AudioProcessor
from engines.rag_retriever import get_rag_retriever
from providers.voice_ai_provider import get_voice_ai_provider
from persistence.session_memory import get_session_memory
from core.prompts import TUTOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

active_voice_sessions: Dict[str, dict] = {}


@router.websocket("/v1/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice conversation.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 PCM audio>"}
    - Client sends: {"type": "end_speech"} when user stops talking
    - Client sends: {"type": "start_session", "session_id": "..."}
    - Server sends: {"type": "transcription", "text": "..."}
    - Server sends: {"type": "response", "text": "...", "audio": "<base64 mp3>"}
    - Server sends: {"type": "status", "status": "listening|processing|speaking"}
    """
    await websocket.accept()

    session_id = str(uuid.uuid4())
    audio_processor = AudioProcessor(sample_rate=16000, vad_threshold=0.3)
    voice_ai = get_voice_ai_provider()
    memory = get_session_memory()
    rag = get_rag_retriever()

    conversation_history = []
    audio_buffer = []
    is_collecting_audio = False

    logger.info(f"Voice WebSocket connected: {session_id}")

    await websocket.send_json({
        "type": "session_started",
        "session_id": session_id
    })

    try:
        while True:
            try:
                message = await websocket.receive()

                if "text" in message:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "audio":
                        audio_data = base64.b64decode(data.get("data", ""))

                        if len(audio_data) > 0:
                            audio_buffer.append(audio_data)

                            has_speech, confidence = audio_processor.detect_voice_activity(audio_data)

                            if has_speech:
                                is_collecting_audio = True
                                audio_processor.add_to_buffer(audio_data)

                            await websocket.send_json({
                                "type": "vad",
                                "has_speech": has_speech,
                                "confidence": round(confidence, 2)
                            })

                    elif msg_type == "end_speech" or msg_type == "process":
                        if audio_buffer:
                            await websocket.send_json({"type": "status", "status": "processing"})

                            combined_audio = b''.join(audio_buffer)
                            audio_buffer = []

                            wav_audio = audio_processor.pcm_to_wav(combined_audio)
                            transcription = await voice_ai.transcribe_audio(wav_audio)

                            if transcription and len(transcription.strip()) > 0:
                                await websocket.send_json({
                                    "type": "transcription",
                                    "text": transcription
                                })

                                rag_context = rag.get_context(transcription) if rag else ""

                                conversation_history.append({
                                    "role": "user",
                                    "content": transcription
                                })

                                ai_response = await voice_ai.generate_response(
                                    user_message=transcription,
                                    conversation_history=conversation_history,
                                    system_prompt=TUTOR_SYSTEM_PROMPT,
                                    context=rag_context if rag_context else None
                                )

                                conversation_history.append({
                                    "role": "assistant",
                                    "content": ai_response
                                })

                                memory.add_message(session_id, "user", transcription)
                                memory.add_message(session_id, "assistant", ai_response)

                                await websocket.send_json({"type": "status", "status": "speaking"})

                                audio_response = await voice_ai.synthesize_speech(ai_response)

                                if audio_response:
                                    await websocket.send_json({
                                        "type": "response",
                                        "text": ai_response,
                                        "audio": base64.b64encode(audio_response).decode('utf-8')
                                    })
                                else:
                                    await websocket.send_json({
                                        "type": "response",
                                        "text": ai_response,
                                        "audio": None
                                    })

                            audio_processor.reset()
                            is_collecting_audio = False

                            await websocket.send_json({"type": "status", "status": "listening"})

                    elif msg_type == "confusion_trigger":
                        screen_context = data.get("screen_context", "studying")

                        await websocket.send_json({"type": "status", "status": "processing"})

                        proactive_message = f"I noticed you might be having trouble with {screen_context}. Would you like me to help explain it?"

                        conversation_history.append({
                            "role": "assistant",
                            "content": proactive_message
                        })

                        await websocket.send_json({"type": "status", "status": "speaking"})

                        audio_response = await voice_ai.synthesize_speech(proactive_message)

                        await websocket.send_json({
                            "type": "proactive_response",
                            "text": proactive_message,
                            "audio": base64.b64encode(audio_response).decode('utf-8') if audio_response else None
                        })

                        await websocket.send_json({"type": "status", "status": "listening"})

                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

                elif "bytes" in message:
                    audio_data = message["bytes"]
                    audio_buffer.append(audio_data)

                    has_speech, confidence = audio_processor.detect_voice_activity(audio_data)

                    if has_speech:
                        is_collecting_audio = True
                        audio_processor.add_to_buffer(audio_data)

            except WebSocketDisconnect:
                logger.info(f"Voice WebSocket disconnected: {session_id}")
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except Exception as e:
        logger.error(f"Voice session error: {e}")
    finally:
        if session_id in active_voice_sessions:
            del active_voice_sessions[session_id]
