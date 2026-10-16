import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from llama_parse import LlamaParse
from persistence.chroma_store import get_chroma_store
from engines.chunking import split_text_recursive
from engines.retrievers import BM25Index, reciprocal_rank_fusion
from engines.reranker import RelevanceReRanker
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
    Split text into overlapping bounded chunks using recursive hierarchical chunking.
    Strictly guarantees that no chunk exceeds chunk_size, fixing paragraph overflow bug.
    """
    return split_text_recursive(text, chunk_size=chunk_size, chunk_overlap=overlap, min_chunk_len=MIN_CHUNK_LEN)

class RAGRetriever:
    """RAG retriever: PDF → LlamaParse → ChromaDB (OpenAI embeddings)."""

    def __init__(self):
        self.chroma = get_chroma_store()
        self.bm25 = BM25Index()
        self.reranker = RelevanceReRanker()
        self.llama_api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

        # Rehydrate BM25 index across server restarts:
        # First try loading from disk; if empty, rehydrate from ChromaDB persistent store
        loaded = self.bm25.load_from_disk()
        if not loaded or sum(len(docs) for docs in self.bm25.corpus.values()) == 0:
            self.rehydrate_bm25_from_chroma()

    async def index_document(self, file_path: str, filename: str, user_id: Optional[str] = None) -> dict:
        """Parse a PDF with LlamaParse and index chunks into ChromaDB."""
        try:
            if not user_id or not str(user_id).strip():
                return {"success": False, "message": "user_id is required to index document"}

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
                    meta = {
                        "source":      filename,
                        "page":        page_idx + 1,
                        "chunk_index": chunk_idx,
                        "user_id":     str(user_id),
                    }
                    metadatas.append(meta)
            if not chunks:
                return {"success": False, "message": "Document appears to have no readable text"}

            self.chroma.add_documents(documents=chunks, metadatas=metadatas, user_id=user_id)
            self.bm25.add_documents(documents=chunks, metadatas=metadatas, user_id=user_id)

            logger.info(f"Indexed '{filename}': {page_count} pages → {len(chunks)} chunks (user_id={user_id})")
            return {
                "success":        True,
                "chunks_indexed": len(chunks),
                "pages":          page_count,
                "message":        f"Indexed {len(chunks)} chunks from {filename} ({page_count} pages)",
            }

        except Exception as e:
            logger.error(f"Error indexing '{filename}': {e}")
            return {"success": False, "message": str(e)}

    def retrieve(
        self,
        query: str,
        user_id: Optional[str] = None,
        n_results: int = 6,
        mode: Optional[str] = None,
    ) -> dict:
        """
        Return top-k chunks most relevant to query for a specific user tenant.
        Modes: 'dense', 'bm25', 'hybrid', 'hybrid_rerank', 'no_rag'
        """
        if not user_id or not str(user_id).strip():
            logger.warning("RAG retrieve called without user_id; returning empty result to enforce tenant scoping")
            return {"query": query, "results": [], "total_found": 0, "mode": mode or "none"}

        retrieval_mode = (mode or os.environ.get("RAG_RETRIEVAL_MODE", "hybrid_rerank")).lower()

        if retrieval_mode == "no_rag":
            return {"query": query, "results": [], "total_found": 0, "mode": "no_rag"}

        try:
            dense_results: List[Dict[str, Any]] = []
            if retrieval_mode in ("dense", "hybrid", "hybrid_rerank"):
                try:
                    raw_chroma = self.chroma.query(query, n_results=n_results * 2 if "hybrid" in retrieval_mode else n_results, user_id=user_id)
                    docs      = raw_chroma.get("documents",  [[]])[0]
                    metas     = raw_chroma.get("metadatas",  [[]])[0]
                    distances = raw_chroma.get("distances",  [[]])[0]
                    dense_results = [
                        {
                            "content":  doc,
                            "metadata": metas[i] if i < len(metas) else {},
                            "score":    round(1 - distances[i], 4) if i < len(distances) else 0.0,
                        }
                        for i, doc in enumerate(docs)
                    ]
                except Exception as de:
                    logger.warning(f"Dense retrieval error: {de}")

            bm25_results: List[Dict[str, Any]] = []
            if retrieval_mode in ("bm25", "hybrid", "hybrid_rerank"):
                try:
                    bm25_results = self.bm25.query(query, n_results=n_results * 2 if "hybrid" in retrieval_mode else n_results, user_id=user_id)
                except Exception as be:
                    logger.warning(f"BM25 retrieval error: {be}")

            # Mode dispatch
            if retrieval_mode == "dense":
                results = dense_results[:n_results]
            elif retrieval_mode == "bm25":
                results = bm25_results[:n_results]
            elif retrieval_mode == "hybrid":
                results = reciprocal_rank_fusion(dense_results, bm25_results, top_n=n_results)
            elif retrieval_mode == "hybrid_rerank":
                fused_candidates = reciprocal_rank_fusion(dense_results, bm25_results, top_n=max(12, n_results * 2))
                results = self.reranker.rerank(query, fused_candidates, top_k=n_results)
            else:
                results = dense_results[:n_results]

            return {
                "query": query,
                "results": results,
                "total_found": len(results),
                "mode": retrieval_mode,
            }
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return {"query": query, "results": [], "total_found": 0, "mode": retrieval_mode}
    def get_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        max_chars: int = 3000,
        mode: Optional[str] = None,
    ) -> str:
        """
        Return a formatted context string for the LLM.
        Filters out chunks with low score so unrelated docs don't pollute the prompt.
        """
        if not user_id or not str(user_id).strip():
            return "No relevant materials found in uploaded documents."
        results = self.retrieve(query, user_id=user_id, mode=mode)
        relevant = [r for r in results["results"] if r.get("score", 0.0) >= 0.20]
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

    def delete_document(self, filename: str, user_id: Optional[str] = None):
        if not user_id or not str(user_id).strip():
            raise ValueError("user_id is required to delete document")
        self.chroma.delete_by_source(filename, user_id=user_id)
        self.bm25.delete_by_source(filename, user_id=user_id)
    def get_indexed_documents(self, user_id: Optional[str] = None) -> List[str]:
        if not user_id or not str(user_id).strip():
            return []
        return self.chroma.list_sources(user_id=user_id)

    def get_document_count(self, user_id: Optional[str] = None) -> int:
        if not user_id or not str(user_id).strip():
            return 0
        return self.chroma.get_document_count(user_id=user_id)

    def rehydrate_bm25_from_chroma(self, user_id: Optional[str] = None):
        """Rehydrate BM25 index from ChromaDB persistent vector store across server restarts."""
        try:
            from collections import defaultdict
            where_clause = {"user_id": str(user_id)} if user_id else None
            data = self.chroma.collection.get(where=where_clause, include=["documents", "metadatas"])
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            if not docs:
                return

            tenant_docs = defaultdict(list)
            tenant_metas = defaultdict(list)
            for i, doc in enumerate(docs):
                m = metas[i] if i < len(metas) else {}
                uid = m.get("user_id") or "default"
                tenant_docs[uid].append(doc)
                tenant_metas[uid].append(m)

            for uid, d_list in tenant_docs.items():
                self.bm25.add_documents(d_list, tenant_metas[uid], user_id=uid, auto_save=False)

            self.bm25.save_to_disk()
            logger.info(f"Rehydrated BM25 index from ChromaDB: {len(docs)} chunks across {len(tenant_docs)} tenants.")
        except Exception as e:
            logger.warning(f"BM25 rehydration from ChromaDB failed: {e}")

# Singleton
_rag_retriever: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever
