import os
import logging
from typing import Optional, List
from pathlib import Path

from llama_parse import LlamaParse
from persistence.chroma_store import get_chroma_store
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

UPLOADS_DIR = os.environ.get("UPLOADS_DIR", "./data/uploads")

# Chunking constants
CHUNK_SIZE     = 800   # target characters per chunk
CHUNK_OVERLAP  = 120   # overlap between consecutive chunks
MIN_CHUNK_LEN  = 60    # skip chunks shorter than this


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping fixed-size chunks.
    Splits on paragraph boundaries first, then merges/splits to hit chunk_size.
    """
    # Normalise whitespace
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_CHUNK_LEN]

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        # If adding this paragraph stays within limit, accumulate
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            # Flush current chunk
            if len(current) >= MIN_CHUNK_LEN:
                chunks.append(current)
            # Start next chunk with overlap from end of last chunk
            overlap_text = current[-overlap:] if overlap and current else ""
            current = (overlap_text + "\n\n" + para).strip() if overlap_text else para

    if len(current) >= MIN_CHUNK_LEN:
        chunks.append(current)

    return chunks


class RAGRetriever:
    """RAG retriever: PDF → LlamaParse → ChromaDB (OpenAI embeddings)."""

    def __init__(self):
        self.chroma = get_chroma_store()
        self.llama_api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

    async def index_document(self, file_path: str, filename: str) -> dict:
        """Parse a PDF with LlamaParse and index chunks into ChromaDB."""
        try:
            if not self.llama_api_key:
                return {"success": False, "message": "LLAMA_CLOUD_API_KEY not configured"}

            parser = LlamaParse(
                api_key=self.llama_api_key,
                result_type="markdown",
                verbose=False,
            )

            documents = parser.load_data(file_path)

            if not documents:
                return {"success": False, "message": "No content extracted from document"}

            chunks: List[str] = []
            metadatas: List[dict] = []
            page_count = len(documents)

            for page_idx, doc in enumerate(documents):
                page_chunks = _split_into_chunks(doc.text)
                for chunk_idx, chunk in enumerate(page_chunks):
                    chunks.append(chunk)
                    metadatas.append({
                        "source":      filename,
                        "page":        page_idx + 1,
                        "chunk_index": chunk_idx,
                    })

            if not chunks:
                return {"success": False, "message": "Document appears to have no readable text"}

            self.chroma.add_documents(documents=chunks, metadatas=metadatas)

            logger.info(f"Indexed '{filename}': {page_count} pages → {len(chunks)} chunks")
            return {
                "success":        True,
                "chunks_indexed": len(chunks),
                "pages":          page_count,
                "message":        f"Indexed {len(chunks)} chunks from {filename} ({page_count} pages)",
            }

        except Exception as e:
            logger.error(f"Error indexing '{filename}': {e}")
            return {"success": False, "message": str(e)}

    def retrieve(self, query: str, n_results: int = 6) -> dict:
        """Return top-k chunks most relevant to query."""
        try:
            raw = self.chroma.query(query, n_results=n_results)
            docs      = raw.get("documents",  [[]])[0]
            metas     = raw.get("metadatas",  [[]])[0]
            distances = raw.get("distances",  [[]])[0]

            results = [
                {
                    "content":  doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "score":    round(1 - distances[i], 4) if i < len(distances) else 0,
                }
                for i, doc in enumerate(docs)
            ]
            return {"query": query, "results": results, "total_found": len(results)}
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return {"query": query, "results": [], "total_found": 0}

    def get_context(self, query: str, max_chars: int = 3000) -> str:
        """
        Return a formatted context string for the LLM.
        Filters to chunks with score >= 0.30 so unrelated docs don't pollute the prompt.
        """
        results = self.retrieve(query)

        relevant = [r for r in results["results"] if r["score"] >= 0.30]
        if not relevant:
            return "No relevant materials found in uploaded documents."

        parts: List[str] = []
        char_count = 0
        for r in relevant:
            content = r["content"]
            source  = r["metadata"].get("source", "Unknown")
            page    = r["metadata"].get("page")
            label   = f"[{source}" + (f" · p.{page}" if page else "") + "]"
            entry   = f"{label}\n{content}"
            if char_count + len(entry) > max_chars:
                break
            parts.append(entry)
            char_count += len(entry)

        return "\n\n---\n\n".join(parts)

    # ── management helpers ─────────────────────────────────────────────────────

    def delete_document(self, filename: str):
        self.chroma.delete_by_source(filename)

    def get_indexed_documents(self) -> List[str]:
        return self.chroma.list_sources()

    def get_document_count(self) -> int:
        return self.chroma.get_document_count()


# Singleton
_rag_retriever: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever
