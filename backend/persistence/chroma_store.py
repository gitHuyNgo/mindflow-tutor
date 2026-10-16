import os
import logging
import uuid
from typing import List, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
except ImportError:
    chromadb = None
    ChromaSettings = None
    OpenAIEmbeddingFunction = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
logger = logging.getLogger(__name__)

CHROMA_DIR = os.environ.get("CHROMA_DIR", "./data/chroma_db")


class ChromaStore:
    """ChromaDB vector store for RAG — uses OpenAI text-embedding-3-small."""

    def __init__(self):
        Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        embedding_fn = OpenAIEmbeddingFunction(
            api_key=os.environ["OPENAI_API_KEY"],
            model_name="text-embedding-3-small",
        )

        try:
            self.collection = self.client.get_or_create_collection(
                name="mindflow_documents",
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            if "embedding function" in str(e).lower() or "conflict" in str(e).lower():
                logger.warning("Embedding function conflict — recreating collection.")
                self.client.delete_collection("mindflow_documents")
                self.collection = self.client.create_collection(
                    name="mindflow_documents",
                    embedding_function=embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                raise

    # ── write ──────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ):
        if not user_id or not str(user_id).strip():
            raise ValueError("Tenant user_id is required to add documents to ChromaDB")

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # Inject tenant user_id into all chunk metadatas
        enriched_metadatas = []
        for meta in metadatas:
            m = dict(meta) if meta else {}
            m["user_id"] = str(user_id)
            enriched_metadatas.append(m)

        self.collection.add(documents=documents, metadatas=enriched_metadatas, ids=ids)
        logger.info(f"ChromaDB: added {len(documents)} chunks (user_id={user_id})")

    def delete_by_source(self, source: str, user_id: Optional[str] = None):
        if not user_id or not str(user_id).strip():
            raise ValueError("Tenant user_id is required to delete documents from ChromaDB")

        where_clause = {"$and": [{"source": source}, {"user_id": str(user_id)}]}

        results = self.collection.get(where=where_clause, include=["metadatas"])
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"ChromaDB: deleted {len(results['ids'])} chunks for '{source}' (user_id={user_id})")
    # ── read ───────────────────────────────────────────────────────────────────

    def query(self, query_text: str, n_results: int = 5, user_id: Optional[str] = None) -> dict:
        if not user_id or not str(user_id).strip():
            raise ValueError("Tenant user_id is required for ChromaDB queries")

        # Clamp to actual collection size to avoid chromadb error
        count = self.collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        n = min(n_results, count)

        where_clause = {"user_id": str(user_id)}

        # Verify if any documents match this tenant before querying
        tenant_docs = self.collection.get(where=where_clause, limit=1)
        if not tenant_docs or not tenant_docs.get("ids"):
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        n = min(n, len(self.collection.get(where=where_clause).get("ids", [])))
        if n == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        return self.collection.query(
            query_texts=[query_text],
            n_results=n,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

    def get_document_count(self, user_id: Optional[str] = None) -> int:
        if not user_id or not str(user_id).strip():
            raise ValueError("Tenant user_id is required to get document count")
        docs = self.collection.get(where={"user_id": str(user_id)})
        return len(docs.get("ids", []))

    def list_sources(self, user_id: Optional[str] = None) -> List[str]:
        if not user_id or not str(user_id).strip():
            raise ValueError("Tenant user_id is required to list document sources")
        where_clause = {"user_id": str(user_id)}
        results = self.collection.get(where=where_clause, include=["metadatas"])
        sources: set = set()
        for meta in results.get("metadatas", []):
            if meta and "source" in meta:
                sources.add(meta["source"])
        return list(sources)

# Singleton
_chroma_store: Optional[ChromaStore] = None


def get_chroma_store() -> ChromaStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaStore()
    return _chroma_store
