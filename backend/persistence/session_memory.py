import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager
logger = logging.getLogger(__name__)

SQLITE_DB_PATH = os.environ.get("SESSION_DB_PATH", "./data/sessions.db")


class SessionMemory:
    """
    Persistent session and conversation management.
    - Multi-instance support with read-through / write-through to MongoDB.
    - Resilient offline / restart persistence via embedded SQLite fallback.
    - Fast RAM cache for active in-flight turns.
    """

    def __init__(self, max_messages_per_session: int = 50, db_path: str = SQLITE_DB_PATH):
        self.sessions: Dict[str, List[dict]] = defaultdict(list)
        self.max_messages = max_messages_per_session
        self.session_metadata: Dict[str, dict] = {}
        self._db = None  # Injected AsyncIOMotorDatabase
        self._sqlite_path = Path(db_path)
        self._init_sqlite()

    def set_db(self, db):
        """Inject an AsyncIOMotorDatabase instance for write-through persistence."""
        self._db = db

    # ── SQLite persistence helpers ─────────────────────────────────────────────

    @contextmanager
    def _get_sqlite_conn(self):
        conn = sqlite3.connect(str(self._sqlite_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_sqlite(self):
        try:
            self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_sqlite_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT,
                        subject TEXT,
                        messages_json TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"[SessionMemory] Failed to initialize SQLite store: {e}")

    def _save_sqlite(self, session_id: str, user_id: Optional[str] = None):
        try:
            messages = self.sessions.get(session_id, [])
            meta = self.session_metadata.get(session_id, {})
            now = datetime.now(timezone.utc).isoformat()
            with self._get_sqlite_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, user_id, title, subject, messages_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        messages_json = excluded.messages_json,
                        updated_at = excluded.updated_at,
                        title = COALESCE(excluded.title, sessions.title),
                        subject = COALESCE(excluded.subject, sessions.subject)
                    """,
                    (
                        session_id,
                        user_id or meta.get("user_id", ""),
                        meta.get("title", "Study Session"),
                        meta.get("subject", ""),
                        json.dumps(messages),
                        meta.get("created_at", now),
                        now,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"[SessionMemory] SQLite write error: {e}")

    def _load_sqlite(self, session_id: str) -> Optional[List[dict]]:
        try:
            if not self._sqlite_path.exists():
                return None
            with self._get_sqlite_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT messages_json, title, subject, created_at, updated_at, user_id FROM sessions WHERE session_id = ?",
                    (session_id,),
                )
                row = cursor.fetchone()
                if row:
                    messages = json.loads(row[0]) if row[0] else []
                    self.sessions[session_id] = messages
                    self.session_metadata[session_id] = {
                        "title": row[1] or "Study Session",
                        "subject": row[2] or "",
                        "created_at": row[3],
                        "updated_at": row[4],
                        "user_id": row[5] or "",
                        "message_count": len(messages),
                    }
                    return messages
        except Exception as e:
            logger.warning(f"[SessionMemory] SQLite read error: {e}")
        return None

    # ── MongoDB persistence helpers ───────────────────────────────────────────

    async def _persist_message_mongo(self, session_id: str, message: dict, user_id: Optional[str] = None):
        """Append one message to MongoDB conversations collection."""
        if self._db is None:
            return
        try:
            update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if user_id:
                update_fields["user_id"] = user_id

            await self._db.conversations.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message},
                    "$set": update_fields,
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "title": "Study Session",
                        "subject": "",
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"[SessionMemory] MongoDB write failed: {e}")

    async def _load_mongo_async(self, session_id: str) -> Optional[List[dict]]:
        if self._db is None:
            return None
        try:
            doc = await self._db.conversations.find_one({"session_id": session_id})
            if doc and "messages" in doc:
                messages = doc.get("messages", [])
                self.sessions[session_id] = messages
                self.session_metadata[session_id] = {
                    "title": doc.get("title", "Study Session"),
                    "subject": doc.get("subject", ""),
                    "created_at": doc.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "updated_at": doc.get("updated_at", datetime.now(timezone.utc).isoformat()),
                    "user_id": doc.get("user_id", ""),
                    "message_count": len(messages),
                }
                # Also sync local SQLite
                self._save_sqlite(session_id)
                return messages
        except Exception as e:
            logger.warning(f"[SessionMemory] MongoDB read failed: {e}")
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        audio_url: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Add a message to RAM and persist to SQLite."""
        if session_id not in self.sessions:
            self._load_sqlite(session_id)

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
                "created_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id or "",
            }
        elif user_id and not self.session_metadata[session_id].get("user_id"):
            self.session_metadata[session_id]["user_id"] = user_id

        self.session_metadata[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.session_metadata[session_id]["message_count"] = len(self.sessions[session_id])

        self._save_sqlite(session_id, user_id=user_id)
        return message

    async def add_message_async(
        self,
        session_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        audio_url: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Add a message, persist to SQLite, and write-through to MongoDB."""
        if session_id not in self.sessions:
            await self.get_history_async(session_id)

        message = self.add_message(session_id, role, content, emotion, audio_url, user_id=user_id)
        await self._persist_message_mongo(session_id, message, user_id=user_id)
        return message

    def get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """Synchronous history retrieval with SQLite read-through on cache miss."""
        if session_id not in self.sessions:
            self._load_sqlite(session_id)
        messages = self.sessions.get(session_id, [])
        return messages[-limit:] if limit else messages

    async def get_history_async(self, session_id: str, limit: int = 10) -> List[dict]:
        """Asynchronous history retrieval with MongoDB and SQLite read-through on cache miss."""
        if session_id not in self.sessions:
            loaded = await self._load_mongo_async(session_id)
            if loaded is None:
                self._load_sqlite(session_id)
        return self.get_history(session_id, limit)

    def get_formatted_history(self, session_id: str, limit: int = 5) -> List[dict]:
        messages = self.get_history(session_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    async def get_formatted_history_async(self, session_id: str, limit: int = 5) -> List[dict]:
        messages = await self.get_history_async(session_id, limit)
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

    async def get_context_summary_async(self, session_id: str) -> str:
        messages = await self.get_history_async(session_id, limit=5)
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
        try:
            with self._get_sqlite_conn() as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
        except Exception as e:
            logger.warning(f"[SessionMemory] SQLite delete error: {e}")

    async def clear_session_async(self, session_id: str):
        self.clear_session(session_id)
        if self._db is not None:
            try:
                await self._db.conversations.delete_one({"session_id": session_id})
            except Exception as e:
                logger.warning(f"[SessionMemory] MongoDB delete failed: {e}")

    def get_active_sessions(self) -> int:
        return len(self.sessions)

    def get_session_user_id(self, session_id: str) -> Optional[str]:
        if session_id in self.session_metadata:
            uid = self.session_metadata[session_id].get("user_id")
            if uid:
                return uid
        if self._sqlite_path.exists():
            try:
                with self._get_sqlite_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0]
            except Exception as e:
                logger.warning(f"[SessionMemory] SQLite get_session_user_id error: {e}")
        return None

    async def get_session_user_id_async(self, session_id: str) -> Optional[str]:
        local_uid = self.get_session_user_id(session_id)
        if local_uid:
            return local_uid
        if self._db is not None:
            try:
                doc = await self._db.conversations.find_one({"session_id": session_id}, {"_id": 0, "user_id": 1})
                if doc and doc.get("user_id"):
                    return doc["user_id"]
            except Exception as e:
                logger.warning(f"[SessionMemory] MongoDB get_session_user_id error: {e}")
        return None
    def has_session(self, session_id: str) -> bool:
        if session_id in self.sessions or session_id in self.session_metadata:
            return True
        if self._sqlite_path.exists():
            try:
                with self._get_sqlite_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
                    if cursor.fetchone():
                        return True
            except Exception as e:
                logger.warning(f"[SessionMemory] SQLite has_session error: {e}")
        return False

    async def has_session_async(self, session_id: str) -> bool:
        if self.has_session(session_id):
            return True
        if self._db is not None:
            try:
                count = await self._db.conversations.count_documents({"session_id": session_id})
                return count > 0
            except Exception as e:
                logger.warning(f"[SessionMemory] MongoDB has_session error: {e}")
        return False

    async def check_session_access_async(self, session_id: str, user_id: str) -> bool:
        """
        Verify that caller user_id is authorized to access session_id.
        Default Deny rule:
        - If session already exists anywhere:
          - MUST have user_id equal to caller user_id.
          - If session has no user_id (unowned / legacy orphan) or different user_id -> returns False.
        - If session does not exist anywhere yet: returns True (new session).
        """
        if not user_id or not str(user_id).strip():
            return False
        exists = await self.has_session_async(session_id)
        if not exists:
            return True
        owner_id = await self.get_session_user_id_async(session_id)
        if not owner_id or owner_id != user_id:
            return False
        return True

    def get_all_sessions(self, user_id: Optional[str] = None) -> List[dict]:
        try:
            if self._sqlite_path.exists():
                with self._get_sqlite_conn() as conn:
                    cursor = conn.cursor()
                    if user_id:
                        cursor.execute(
                            "SELECT session_id, title, subject, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 50",
                            (user_id,)
                        )
                    else:
                        cursor.execute(
                            "SELECT session_id, title, subject, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 50"
                        )
                    rows = cursor.fetchall()
                    if rows:
                        return [
                            {
                                "session_id": r[0],
                                "title": r[1] or "Study Session",
                                "subject": r[2] or "",
                                "created_at": r[3],
                                "updated_at": r[4],
                            }
                            for r in rows
                        ]
        except Exception as e:
            logger.warning(f"[SessionMemory] SQLite get_all_sessions error: {e}")

        return [
            {"session_id": sid, **self.session_metadata.get(sid, {})}
            for sid in self.sessions.keys()
            if not user_id or self.session_metadata.get(sid, {}).get("user_id") == user_id
        ]

    async def get_all_sessions_async(self, user_id: Optional[str] = None) -> List[dict]:
        if self._db is not None:
            try:
                query = {"user_id": user_id} if user_id else {}
                cursor = self._db.conversations.find(
                    query,
                    {
                        "_id": 0,
                        "session_id": 1,
                        "title": 1,
                        "subject": 1,
                        "created_at": 1,
                        "updated_at": 1,
                        "messages": 1,
                    },
                ).sort("updated_at", -1).limit(50)
                docs = await cursor.to_list(length=50)
                if docs:
                    return [
                        {
                            "session_id": d.get("session_id"),
                            "title": d.get("title", "Study Session"),
                            "subject": d.get("subject", ""),
                            "created_at": d.get("created_at"),
                            "updated_at": d.get("updated_at"),
                            "message_count": len(d.get("messages", [])),
                        }
                        for d in docs
                    ]
            except Exception as e:
                logger.warning(f"[SessionMemory] MongoDB get_all_sessions failed: {e}")
        return self.get_all_sessions(user_id=user_id)

# Singleton instance
_session_memory: Optional[SessionMemory] = None


def get_session_memory() -> SessionMemory:
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory
