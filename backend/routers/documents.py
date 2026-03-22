import os

import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File

from schemas.models import DocumentUploadResponse, DocumentInfo
from engines.rag_retriever import get_rag_retriever
from core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])


def _get_uploads_dir() -> Path:
    path = Path(os.environ.get("UPLOADS_DIR", "./data/uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/v1/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a PDF document"""
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        logger.info(f"Uploading document: {file.filename}")

        uploads_dir = _get_uploads_dir()
        doc_id    = str(uuid.uuid4())
        file_path = uploads_dir / f"{doc_id}_{file.filename}"

        # Stream to disk while enforcing size limit
        written = 0
        with open(file_path, "wb") as buf:
            while chunk := await file.read(1024 * 256):  # 256 KB chunks
                written += len(chunk)
                if written > MAX_PDF_BYTES:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="PDF exceeds 50 MB limit")
                buf.write(chunk)

        rag = get_rag_retriever()
        result = await rag.index_document(str(file_path), file.filename)

        if not result["success"]:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=result["message"])

        db = get_db()
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


@router.get("/v1/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all indexed documents"""
    try:
        db = get_db()
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


@router.delete("/v1/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    try:
        db = get_db()
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
