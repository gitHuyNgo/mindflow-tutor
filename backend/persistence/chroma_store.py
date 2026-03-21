import os
import logging
import uuid
from typing import List, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CHROMA_DIR = os.environ.get("CHROMA_DIR", "/app/data/chroma_db")


class ChromaStore:
    """ChromaDB vector store for RAG"""
    
    def __init__(self):
        # Ensure directory exists
        Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="mindflow_documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(
        self, 
        documents: List[str], 
        metadatas: List[dict],
        ids: Optional[List[str]] = None
    ):
        """Add documents to the collection"""
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(documents)} documents to ChromaDB")
    
    def query(self, query_text: str, n_results: int = 5) -> dict:
        """Query the collection for similar documents"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return results
    
    def delete_by_source(self, source: str):
        """Delete all documents from a specific source"""
        # Get all IDs for this source
        results = self.collection.get(
            where={"source": source},
            include=["metadatas"]
        )
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} documents from source: {source}")
    
    def get_document_count(self) -> int:
        """Get total number of documents in collection"""
        return self.collection.count()
    
    def list_sources(self) -> List[str]:
        """List all unique document sources"""
        results = self.collection.get(include=["metadatas"])
        sources = set()
        for metadata in results.get("metadatas", []):
            if metadata and "source" in metadata:
                sources.add(metadata["source"])
        return list(sources)


# Singleton instance
_chroma_store: Optional[ChromaStore] = None

def get_chroma_store() -> ChromaStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaStore()
    return _chroma_store