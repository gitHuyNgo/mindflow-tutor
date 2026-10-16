from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from core.auth import SECRET_KEY, ALGORITHM
from routers.conversations import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _make_token(user_id: str, email: str = "test@example.com") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_conversations_endpoints_require_authentication():
    # POST /v1/sessions
    res = client.post("/v1/sessions", json={"session_id": "s1", "title": "Math"})
    assert res.status_code == 401

    # GET /v1/sessions
    res = client.get("/v1/sessions")
    assert res.status_code == 401

    # GET /v1/sessions/{session_id}/messages
    res = client.get("/v1/sessions/s1/messages")
    assert res.status_code == 401

    # GET /v1/conversations/{session_id}
    res = client.get("/v1/conversations/s1")
    assert res.status_code == 401

    # GET /v1/conversations
    res = client.get("/v1/conversations")
    assert res.status_code == 401

    # DELETE /v1/conversations/{session_id}
    res = client.delete("/v1/conversations/s1")
    assert res.status_code == 401


def test_session_ownership_enforcement():
    token_user_a = _make_token("user_a", "a@test.com")
    token_user_b = _make_token("user_b", "b@test.com")
    headers_a = {"Authorization": f"Bearer {token_user_a}"}
    headers_b = {"Authorization": f"Bearer {token_user_b}"}

    # Mock DB
    mock_db = MagicMock()
    mock_conversations = MagicMock()
    mock_db.conversations = mock_conversations

    # Scenario: session "s100" exists and belongs to user_a
    mock_conversations.find_one = AsyncMock(return_value={
        "session_id": "s100",
        "user_id": "user_a",
        "messages": [{"role": "user", "content": "hello"}],
    })
    mock_conversations.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    with patch("routers.conversations.get_db", return_value=mock_db):
        # User B tries to update User A's session -> 403 Forbidden
        res = client.post(
            "/v1/sessions",
            headers=headers_b,
            json={"session_id": "s100", "title": "Hijacked Session"},
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        # User B tries to read User A's messages -> 403 Forbidden
        res = client.get("/v1/sessions/s100/messages", headers=headers_b)
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        # User A reads own messages -> 200 OK
        res = client.get("/v1/sessions/s100/messages", headers=headers_a)
        assert res.status_code == 200
        assert len(res.json()["messages"]) == 1


def test_list_sessions_filters_by_user():
    token_user_a = _make_token("user_a", "a@test.com")
    headers_a = {"Authorization": f"Bearer {token_user_a}"}

    mock_db = MagicMock()
    mock_conversations = MagicMock()
    mock_db.conversations = mock_conversations

    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[
        {"session_id": "s_a", "title": "User A Session", "subject": "Math", "created_at": "", "updated_at": ""}
    ])
    mock_conversations.find.return_value = mock_cursor

    with patch("routers.conversations.get_db", return_value=mock_db):
        res = client.get("/v1/sessions", headers=headers_a)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["session_id"] == "s_a"

        # Verify MongoDB was queried with {"user_id": "user_a"}
        call_args = mock_conversations.find.call_args
        assert call_args[0][0] == {"user_id": "user_a"}

def test_unowned_legacy_session_default_deny():
    token_user_a = _make_token("user_a", "a@test.com")
    headers_a = {"Authorization": f"Bearer {token_user_a}"}

    mock_db = MagicMock()
    mock_conversations = MagicMock()
    mock_db.conversations = mock_conversations

    # Legacy unowned session (user_id is None / empty)
    mock_conversations.find_one = AsyncMock(return_value={
        "session_id": "s_legacy_orphan",
        "user_id": None,
        "messages": [{"role": "user", "content": "orphan message"}],
    })

    with patch("routers.conversations.get_db", return_value=mock_db):
        # Trying to modify unowned legacy session must be rejected with 403 (default-deny)
        res = client.post(
            "/v1/sessions",
            headers=headers_a,
            json={"session_id": "s_legacy_orphan", "title": "Claiming orphan"},
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]

        # Trying to read unowned legacy session must be rejected with 403
        res_read = client.get("/v1/sessions/s_legacy_orphan/messages", headers=headers_a)
        assert res_read.status_code == 403
        assert "Not authorized" in res_read.json()["detail"]
