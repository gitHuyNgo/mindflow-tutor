import io
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from core.auth import SECRET_KEY, ALGORITHM
from routers.documents import router

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


def test_documents_require_authentication():
    # POST /v1/documents/upload
    files = {"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")}
    res = client.post("/v1/documents/upload", files=files)
    assert res.status_code == 401

    # GET /v1/documents
    res = client.get("/v1/documents")
    assert res.status_code == 401

    # DELETE /v1/documents/{document_id}
    res = client.delete("/v1/documents/doc123")
    assert res.status_code == 401


def test_list_documents_tenant_isolation():
    token_user_a = _make_token("user_a")
    headers_a = {"Authorization": f"Bearer {token_user_a}"}

    mock_db = MagicMock()
    mock_docs = MagicMock()
    mock_db.documents = mock_docs

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[
        {"id": "d1", "filename": "user_a_notes.pdf", "upload_date": "2026-10-15", "pages": 5, "size_bytes": 1024}
    ])
    mock_docs.find.return_value = mock_cursor

    with patch("routers.documents.get_db", return_value=mock_db):
        res = client.get("/v1/documents", headers=headers_a)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == "d1"
        assert data[0]["filename"] == "user_a_notes.pdf"

        # Verify MongoDB was strictly queried with {"user_id": "user_a"}
        call_args = mock_docs.find.call_args
        assert call_args[0][0] == {"user_id": "user_a"}


def test_delete_document_ownership_enforcement():
    token_user_b = _make_token("user_b")
    headers_b = {"Authorization": f"Bearer {token_user_b}"}

    mock_db = MagicMock()
    mock_docs = MagicMock()
    mock_db.documents = mock_docs

    # Document belongs to user_a
    mock_docs.find_one = AsyncMock(return_value={
        "id": "doc_a",
        "user_id": "user_a",
        "filename": "confidential.pdf",
        "file_path": "/tmp/confidential.pdf",
    })

    with patch("routers.documents.get_db", return_value=mock_db):
        res = client.delete("/v1/documents/doc_a", headers=headers_b)
        assert res.status_code == 403
        assert "Not authorized" in res.json()["detail"]


def test_upload_document_scopes_user():
    token_user_a = _make_token("user_a")
    headers_a = {"Authorization": f"Bearer {token_user_a}"}

    mock_db = MagicMock()
    mock_docs = MagicMock()
    mock_db.documents = mock_docs
    mock_docs.insert_one = AsyncMock(return_value=MagicMock())

    mock_rag = MagicMock()
    mock_rag.index_document = AsyncMock(return_value={"success": True, "message": "OK", "pages": 2, "chunks_indexed": 4})

    with patch("routers.documents.get_db", return_value=mock_db), \
         patch("routers.documents.get_rag_retriever", return_value=mock_rag), \
         patch("routers.documents._get_uploads_dir", return_value=io.Path("./data/test_uploads") if hasattr(io, "Path") else MagicMock()):
        
        file_content = b"%PDF-1.4 dummy content"
        files = {"file": ("algebra.pdf", file_content, "application/pdf")}

        with patch("builtins.open", MagicMock()):
            with patch("pathlib.Path.stat", return_value=MagicMock(st_size=len(file_content))):
                res = client.post("/v1/documents/upload", headers=headers_a, files=files)
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert data["filename"] == "algebra.pdf"

                # Verify RAG was indexed with user_id="user_a"
                mock_rag.index_document.assert_called_once()
                call_kwargs = mock_rag.index_document.call_args[1]
                assert call_kwargs["user_id"] == "user_a"

                # Verify DB inserted with user_id="user_a"
                mock_docs.insert_one.assert_called_once()
                inserted_doc = mock_docs.insert_one.call_args[0][0]
                assert inserted_doc["user_id"] == "user_a"
