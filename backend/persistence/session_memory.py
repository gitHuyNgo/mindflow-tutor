import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class SessionMemory:
    """In-memory session and conversation management with optional MongoDB write-through"""

    def __init__(self, max_messages_per_session: int = 50):
        self.sessions: Dict[str, List[dict]] = defaultdict(list)
        self.max_messages = max_messages_per_session
        self.session_metadata: Dict[str, dict] = {}
        self._db = None  # injected lazily

    def set_db(self, db):
        """Inject an AsyncIOMotorDatabase instance for write-through persistence."""
        self._db = db

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _persist_message(self, session_id: str, message: dict):
        """Append one message to the MongoDB conversations collection (fire-and-forget friendly)."""
        if self._db is None:
            return
        try:
            await self._db.conversations.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                    "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()},
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"[SessionMemory] MongoDB write failed: {e}")

    # ── public API ────────────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        audio_url: Optional[str] = None,
    ):
        """Add a message to in-memory store (synchronous, for backwards compat)."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "emotion": emotion,
            "audio_url": audio_url,
        }
        self.sessions[session_id].append(message)

        if len(self.sessions[session_id]) > self.max_messages:
            self.sessions[session_id] = self.sessions[session_id][-self.max_messages :]

        if session_id not in self.session_metadata:
            self.session_metadata[session_id] = {
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        self.session_metadata[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.session_metadata[session_id]["message_count"] = len(self.sessions[session_id])

        return message  # returned so async callers can persist it

    async def add_message_async(
        self,
        session_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        audio_url: Optional[str] = None,
    ):
        """Add a message and persist to MongoDB."""
        message = self.add_message(session_id, role, content, emotion, audio_url)
        await self._persist_message(session_id, message)

    def get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        messages = self.sessions.get(session_id, [])
        return messages[-limit:] if limit else messages

    def get_formatted_history(self, session_id: str, limit: int = 5) -> List[dict]:
        messages = self.get_history(session_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    def get_context_summary(self, session_id: str) -> str:
        messages = self.get_history(session_id, limit=5)
        if not messages:
            return "No previous conversation."
        parts = []
        for msg in messages:
            role = "Student" if msg["role"] == "user" else "Tutor"
            parts.append(f"{role}: {msg['content'][:100]}...")
        return "\n".join(parts)

    def clear_session(self, session_id: str):
        self.sessions.pop(session_id, None)
        self.session_metadata.pop(session_id, None)

    def get_active_sessions(self) -> int:
        return len(self.sessions)

    def get_all_sessions(self) -> List[dict]:
        return [
            {"session_id": sid, **self.session_metadata.get(sid, {})}
            for sid in self.sessions.keys()
        ]


# Singleton instance
_session_memory: Optional[SessionMemory] = None


def get_session_memory() -> SessionMemory:
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory
