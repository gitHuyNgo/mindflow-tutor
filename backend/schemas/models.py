from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class EmotionState(str, Enum):
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FOCUSED = "focused"
    FRUSTRATED = "frustrated"


class ProcessTriggerRequest(BaseModel):
    """Request model for processing confusion trigger"""
    screen_capture: str = Field(..., description="Base64 encoded screen capture")
    emotion_state: EmotionState = Field(default=EmotionState.CONFUSED)
    user_query: Optional[str] = Field(None, description="Optional explicit question from user")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ProcessTriggerResponse(BaseModel):
    """Response model for confusion trigger processing"""
    session_id: str
    text_response: str
    audio_available: bool = False
    screen_analysis: Optional[str] = None
    sources_used: List[str] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    document_id: str
    filename: str
    pages: int
    status: str
    message: str


class DocumentInfo(BaseModel):
    """Information about an indexed document"""
    id: str
    filename: str
    upload_date: str
    pages: int
    size_bytes: int


class ConversationMessage(BaseModel):
    """A single conversation message"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    audio_url: Optional[str] = None
    emotion_detected: Optional[EmotionState] = None


class ConversationHistory(BaseModel):
    """Full conversation history for a session"""
    session_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SettingsUpdate(BaseModel):
    """Model for updating settings"""
    voice_id: Optional[str] = None
    auto_response: Optional[bool] = None
    confusion_threshold: Optional[float] = None


class SystemStatus(BaseModel):
    """System status information"""
    rag_ready: bool
    documents_indexed: int
    active_sessions: int
    last_activity: Optional[str] = None


class SearchRequest(BaseModel):
    """Request for web search"""
    query: str
    max_results: int = 5


class SearchResult(BaseModel):
    """A single search result"""
    title: str
    url: str
    content: str
    score: float


class SearchResponse(BaseModel):
    """Response from web search"""
    query: str
    results: List[SearchResult]
    answer: Optional[str] = None