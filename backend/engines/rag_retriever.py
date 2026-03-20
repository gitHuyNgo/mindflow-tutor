import os
import logging
from typing import Optional, List
from pathlib import Path
from llama_parse import LlamaParse
from persistence.chroma_store import get_chroma_store
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

UPLOADS_DIR = os.environ.get("UPLOADS_DIR", "/app/data/uploads")


class RAGRetriever:
    """RAG retriever using LlamaParse and ChromaDB"""
    
    def __init__(self):
        self.chroma = get_chroma_store()
        self.llama_api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        
        # Ensure uploads directory exists
        Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    
    async def index_document(self, file_path: str, filename: str) -> dict:
        """Parse and index a PDF document"""
        try:
            # Initialize LlamaParse
            parser = LlamaParse(
                api_key=self.llama_api_key,
                result_type="markdown",
                verbose=False
            )
            
            # Parse the document
            documents = parser.load_data(file_path)
            
            if not documents:
                return {
                    "success": False,
                    "message": "No content extracted from document"
                }
            
            # Chunk the document for better retrieval
            chunks = []
            metadatas = []
            
            for doc in documents:
                text = doc.text
                # Simple chunking by paragraphs
                paragraphs = text.split('\n\n')
                
                for i, para in enumerate(paragraphs):
                    if len(para.strip()) > 50:  # Skip very short paragraphs
                        chunks.append(para.strip())
                        metadatas.append({
                            "source": filename,
                            "chunk_index": i,
                            "total_chunks": len(paragraphs)
                        })
            
            # Add to ChromaDB
            if chunks:
                self.chroma.add_documents(
                    documents=chunks,
                    metadatas=metadatas
                )
            
            return {
                "success": True,
                "chunks_indexed": len(chunks),
                "pages": len(documents),
                "message": f"Successfully indexed {len(chunks)} chunks from {filename}"
            }
            
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def retrieve(self, query: str, n_results: int = 5) -> dict:
        """Retrieve relevant documents for a query"""
        try:
            results = self.chroma.query(query, n_results=n_results)
            
            # Format results
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            formatted_results = []
            for i, doc in enumerate(documents):
                formatted_results.append({
                    "content": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "score": 1 - distances[i] if i < len(distances) else 0  # Convert distance to similarity
                })
            
            return {
                "query": query,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return {
                "query": query,
                "results": [],
                "total_found": 0
            }
    
    def get_context(self, query: str, max_chars: int = 2000) -> str:
        """Get formatted context string for LLM prompt"""
        results = self.retrieve(query)
        
        if not results["results"]:
            return "No relevant materials found in uploaded documents."
        
        context_parts = []
        char_count = 0
        
        for result in results["results"]:
            content = result["content"]
            source = result["metadata"].get("source", "Unknown")
            
            if char_count + len(content) > max_chars:
                break
            
            context_parts.append(f"[From: {source}]\n{content}")
            char_count += len(content)
        
        return "\n\n".join(context_parts)
    
    def delete_document(self, filename: str):
        """Delete a document from the index"""
        self.chroma.delete_by_source(filename)
    
    def get_indexed_documents(self) -> List[str]:
        """Get list of indexed document sources"""
        return self.chroma.list_sources()
    
    def get_document_count(self) -> int:
        """Get total number of indexed chunks"""
        return self.chroma.get_document_count()


# Singleton instance
_rag_retriever: Optional[RAGRetriever] = None

def get_rag_retriever() -> RAGRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever
