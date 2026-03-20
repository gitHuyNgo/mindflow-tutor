import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class SessionMemory:
    """In-memory session and conversation management"""
    
    def __init__(self, max_messages_per_session: int = 50):
        self.sessions: Dict[str, List[dict]] = defaultdict(list)
        self.max_messages = max_messages_per_session
        self.session_metadata: Dict[str, dict] = {}
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        emotion: Optional[str] = None,
        audio_url: Optional[str] = None
    ):
        """Add a message to a session"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion,
            "audio_url": audio_url
        }
        self.sessions[session_id].append(message)
        
        # Trim if exceeds max
        if len(self.sessions[session_id]) > self.max_messages:
            self.sessions[session_id] = self.sessions[session_id][-self.max_messages:]
        
        # Update metadata
        if session_id not in self.session_metadata:
            self.session_metadata[session_id] = {
                "created_at": datetime.now().isoformat()
            }
        self.session_metadata[session_id]["updated_at"] = datetime.now().isoformat()
        self.session_metadata[session_id]["message_count"] = len(self.sessions[session_id])
    
    def get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """Get conversation history for a session"""
        messages = self.sessions.get(session_id, [])
        return messages[-limit:] if limit else messages
    
    def get_formatted_history(self, session_id: str, limit: int = 5) -> List[dict]:
        """Get history formatted for OpenAI API"""
        messages = self.get_history(session_id, limit)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
    
    def get_context_summary(self, session_id: str) -> str:
        """Get a text summary of recent conversation context"""
        messages = self.get_history(session_id, limit=5)
        if not messages:
            return "No previous conversation."
        
        summary_parts = []
        for msg in messages:
            role = "Student" if msg["role"] == "user" else "Tutor"
            summary_parts.append(f"{role}: {msg['content'][:100]}...")
        
        return "\n".join(summary_parts)
    
    def clear_session(self, session_id: str):
        """Clear a session's history"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]
    
    def get_active_sessions(self) -> int:
        """Get count of active sessions"""
        return len(self.sessions)
    
    def get_all_sessions(self) -> List[dict]:
        """Get metadata for all sessions"""
        return [
            {
                "session_id": sid,
                **self.session_metadata.get(sid, {})
            }
            for sid in self.sessions.keys()
        ]


# Singleton instance
_session_memory: Optional[SessionMemory] = None

def get_session_memory() -> SessionMemory:
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory
