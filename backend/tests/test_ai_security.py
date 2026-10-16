from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from core.auth import SECRET_KEY, ALGORITHM
from routers.ai import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _make_token(user_id: str, email: str = "test@example.com") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_ai_endpoints_reject_unauthenticated():
    # POST /v1/process-trigger
    res = client.post("/v1/process-trigger", json={"screen_capture": "dGVzdA=="})
    assert res.status_code == 401

    # POST /v1/ask
    res = client.post("/v1/ask?question=What+is+calculus")
    assert res.status_code == 401

    # POST /v1/detector/frame
    res = client.post("/v1/detector/frame", json={"image_base64": "dGVzdA=="})
    assert res.status_code == 401


def test_process_trigger_rejects_user_id_spoofing():
    token_alice = _make_token("user_alice")
    headers = {"Authorization": f"Bearer {token_alice}"}

    # Alice attempts to specify user_bob's id in request payload
    res = client.post(
        "/v1/process-trigger",
        headers=headers,
        json={
            "screen_capture": "dGVzdA==",
            "user_id": "user_bob",  # Spoofing attempt
            "session_id": "session_123",
        },
    )
    assert res.status_code == 403
    assert "user_id mismatch" in res.json()["detail"]


def test_process_trigger_rejects_foreign_session():
    token_alice = _make_token("user_alice")
    headers = {"Authorization": f"Bearer {token_alice}"}

    mock_memory = MagicMock()
    # check_session_access_async returns False (session belongs to Bob)
    mock_memory.check_session_access_async = AsyncMock(return_value=False)

    with patch("routers.ai.get_session_memory", return_value=mock_memory):
        res = client.post(
            "/v1/process-trigger",
            headers=headers,
            json={
                "screen_capture": "dGVzdA==",
                "session_id": "session_bob_private",
            },
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]


def test_ask_rejects_foreign_session():
    token_alice = _make_token("user_alice")
    headers = {"Authorization": f"Bearer {token_alice}"}

    mock_memory = MagicMock()
    mock_memory.check_session_access_async = AsyncMock(return_value=False)

    with patch("routers.ai.get_session_memory", return_value=mock_memory):
        res = client.post(
            "/v1/ask?question=Explain+Newton+Laws&session_id=session_bob_private",
            headers=headers,
        )
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]


def test_detector_frame_rejects_user_id_spoofing():
    token_alice = _make_token("user_alice")
    headers = {"Authorization": f"Bearer {token_alice}"}

    res = client.post(
        "/v1/detector/frame",
        headers=headers,
        json={
            "image_base64": "dGVzdA==",
            "user_id": "user_bob",  # Spoofing attempt
        },
    )
    assert res.status_code == 403
    assert "user_id mismatch" in res.json()["detail"]
