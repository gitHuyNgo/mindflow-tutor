from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from passlib.context import CryptContext
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import shutil
import base64
import json
import asyncio

# Load environment before imports
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Local imports
from schemas.models import (
    ProcessTriggerRequest, ProcessTriggerResponse,
    DocumentUploadResponse, DocumentInfo,
    ConversationMessage, ConversationHistory,
    SettingsUpdate, SystemStatus,
    SearchRequest, SearchResponse, SearchResult
)
from engines.orchestrator import get_orchestrator
from engines.rag_retriever import get_rag_retriever
from engines.audio_processor import AudioProcessor
from providers.elevenlabs_provider import get_elevenlabs_provider
from providers.tavily_provider import get_tavily_provider
from providers.voice_ai_provider import get_voice_ai_provider
from persistence.session_memory import get_session_memory
from core.prompts import TUTOR_SYSTEM_PROMPT
from routers.auth import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_ADMIN_SEED = {
    "full_name": "admin",
    "email":     "admin1234.test@gmail.com",
    "password":  "admin1234",
    "role":      "admin",
}


async def _seed_admin():
    existing = await db.users.find_one({"email": _ADMIN_SEED["email"]})
    if existing:
        return
    doc = {
        "id":                     str(uuid.uuid4()),
        "email":                  _ADMIN_SEED["email"],
        "full_name":              _ADMIN_SEED["full_name"],
        "hashed_password":        _pwd_ctx.hash(_ADMIN_SEED["password"]),
        "role":                   _ADMIN_SEED["role"],
        "is_verified":            True,
        "verification_token":     None,
        "verification_token_exp": None,
        "created_at":             datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    logger.info(f"[seed] Admin account created: {_ADMIN_SEED['email']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_admin()
    yield
    client.close()

# Create the main app
app = FastAPI(
    title="MindFlow Tutor API",
    description="Proactive Multimodal AI Learning Assistant with Voice",
    version="2.0.0",
    lifespan=lifespan
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Uploads directory
UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", "/app/data/uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Store active WebSocket sessions
active_voice_sessions: Dict[str, dict] = {}


# ============== Basic Routes ==============

@api_router.get("/")
async def root():
    return {"message": "MindFlow Tutor API", "version": "2.0.0", "voice_enabled": True}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============== WebSocket Voice Chat ==============

@api_router.websocket("/v1/voice")
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
    
    # Send session info
    await websocket.send_json({
        "type": "session_started",
        "session_id": session_id
    })
    
    try:
        while True:
            try:
                # Receive message (can be text JSON or binary audio)
                message = await websocket.receive()
                
                if "text" in message:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "audio":
                        # Receive base64 encoded audio chunk
                        audio_data = base64.b64decode(data.get("data", ""))
                        
                        if len(audio_data) > 0:
                            # Add to buffer
                            audio_buffer.append(audio_data)
                            
                            # Check VAD
                            has_speech, confidence = audio_processor.detect_voice_activity(audio_data)
                            
                            if has_speech:
                                is_collecting_audio = True
                                audio_processor.add_to_buffer(audio_data)
                            
                            # Send VAD status
                            await websocket.send_json({
                                "type": "vad",
                                "has_speech": has_speech,
                                "confidence": round(confidence, 2)
                            })
                    
                    elif msg_type == "end_speech" or msg_type == "process":
                        # User finished speaking, process the audio
                        if audio_buffer:
                            await websocket.send_json({"type": "status", "status": "processing"})
                            
                            # Combine all audio chunks
                            combined_audio = b''.join(audio_buffer)
                            audio_buffer = []
                            
                            # Convert to WAV format for Whisper
                            wav_audio = audio_processor.pcm_to_wav(combined_audio)
                            
                            # Transcribe
                            transcription = await voice_ai.transcribe_audio(wav_audio)
                            
                            if transcription and len(transcription.strip()) > 0:
                                await websocket.send_json({
                                    "type": "transcription",
                                    "text": transcription
                                })
                                
                                # Get RAG context
                                rag_context = rag.get_context(transcription) if rag else ""
                                
                                # Add to conversation history
                                conversation_history.append({
                                    "role": "user",
                                    "content": transcription
                                })
                                
                                # Generate AI response
                                ai_response = await voice_ai.generate_response(
                                    user_message=transcription,
                                    conversation_history=conversation_history,
                                    system_prompt=TUTOR_SYSTEM_PROMPT,
                                    context=rag_context if rag_context else None
                                )
                                
                                # Add to history
                                conversation_history.append({
                                    "role": "assistant",
                                    "content": ai_response
                                })
                                
                                # Store in memory
                                memory.add_message(session_id, "user", transcription)
                                memory.add_message(session_id, "assistant", ai_response)
                                
                                # Generate TTS
                                await websocket.send_json({"type": "status", "status": "speaking"})
                                
                                audio_response = await voice_ai.synthesize_speech(ai_response)
                                
                                if audio_response:
                                    await websocket.send_json({
                                        "type": "response",
                                        "text": ai_response,
                                        "audio": base64.b64encode(audio_response).decode('utf-8')
                                    })
                                else:
                                    # Send text-only response if TTS fails
                                    await websocket.send_json({
                                        "type": "response",
                                        "text": ai_response,
                                        "audio": None
                                    })
                            
                            audio_processor.reset()
                            is_collecting_audio = False
                            
                            await websocket.send_json({"type": "status", "status": "listening"})
                    
                    elif msg_type == "confusion_trigger":
                        # Bot speaks first due to confusion detection
                        screen_context = data.get("screen_context", "studying")
                        
                        await websocket.send_json({"type": "status", "status": "processing"})
                        
                        proactive_message = f"I noticed you might be having trouble with {screen_context}. Would you like me to help explain it?"
                        
                        conversation_history.append({
                            "role": "assistant",
                            "content": proactive_message
                        })
                        
                        # Generate TTS for proactive message
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
                    # Direct binary audio
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


# ============== Main Trigger Endpoint (for confusion detection) ==============

@api_router.post("/v1/process-trigger", response_model=dict)
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


@api_router.post("/v1/ask", response_model=dict)
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


# ============== TTS Endpoints ==============

@api_router.post("/v1/tts/stream")
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


@api_router.post("/v1/tts/generate", response_model=dict)
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


# ============== Document Management ==============

@api_router.post("/v1/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a PDF document"""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        doc_id = str(uuid.uuid4())
        file_path = UPLOADS_DIR / f"{doc_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        rag = get_rag_retriever()
        result = await rag.index_document(str(file_path), file.filename)
        
        if not result["success"]:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=result["message"])
        
        doc_info = {
            "id": doc_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "upload_date": datetime.now(timezone.utc).isoformat(),
            "pages": result.get("pages", 0),
            "chunks": result.get("chunks_indexed", 0),
            "size_bytes": file_path.stat().st_size
        }
        await db.documents.insert_one(doc_info)
        
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            pages=result.get("pages", 0),
            status="success",
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/v1/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all indexed documents"""
    try:
        documents = await db.documents.find({}, {"_id": 0}).to_list(100)
        return [
            DocumentInfo(
                id=doc["id"],
                filename=doc["filename"],
                upload_date=doc["upload_date"],
                pages=doc.get("pages", 0),
                size_bytes=doc.get("size_bytes", 0)
            )
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/v1/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    try:
        doc = await db.documents.find_one({"id": document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        rag = get_rag_retriever()
        rag.delete_document(doc["filename"])
        
        file_path = Path(doc["file_path"])
        file_path.unlink(missing_ok=True)
        
        await db.documents.delete_one({"id": document_id})
        
        return {"status": "deleted", "document_id": document_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Agora Token Generation ==============

@api_router.get("/v1/agora/config")
async def get_agora_config():
    """Get Agora configuration for client"""
    return {
        "app_id": os.environ.get("AGORA_APP_ID"),
        "channel": "mindflow-voice"
    }


# ============== System Status ==============

@api_router.get("/v1/status", response_model=SystemStatus)
async def get_status():
    """Get system status"""
    try:
        rag = get_rag_retriever()
        memory = get_session_memory()
        
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


# ============== Conversations ==============

@api_router.get("/v1/conversations/{session_id}", response_model=ConversationHistory)
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


@api_router.get("/v1/conversations", response_model=List[dict])
async def list_sessions():
    """List all sessions"""
    try:
        memory = get_session_memory()
        return memory.get_all_sessions()
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/v1/conversations/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation"""
    try:
        memory = get_session_memory()
        memory.clear_session(session_id)
        return {"status": "cleared", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Search ==============

@api_router.post("/v1/search", response_model=SearchResponse)
async def web_search(request: SearchRequest):
    """Perform a web search using Tavily"""
    try:
        tavily = await get_tavily_provider()
        results = await tavily.search(request.query, max_results=request.max_results)
        
        return SearchResponse(
            query=results["query"],
            results=[
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    content=r["content"],
                    score=r["score"]
                )
                for r in results["results"]
            ],
            answer=results.get("answer")
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Include the router in the main app
api_router.include_router(auth_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)