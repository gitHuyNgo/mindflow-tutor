import os
import tempfile
from unittest.mock import MagicMock
from engines.retrievers import BM25Index
from engines.rag_retriever import RAGRetriever


def test_bm25_disk_persistence_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        disk_path = os.path.join(tmpdir, "bm25_test.json")

        # Instance 1: create index and save
        bm25_1 = BM25Index(persistence_path=disk_path)
        docs = [
            "Newton's laws of motion form the foundation of classical mechanics.",
            "Photosynthesis in green plants synthesizes glucose from carbon dioxide.",
        ]
        metas = [{"source": "physics.pdf"}, {"source": "biology.pdf"}]
        bm25_1.add_documents(docs, metas, user_id="user_alice")
        assert os.path.exists(disk_path)

        # Instance 2: new instance with empty RAM loads from disk
        bm25_2 = BM25Index(persistence_path=disk_path)
        loaded = bm25_2.load_from_disk()
        assert loaded is True
        assert "user_alice" in bm25_2.corpus
        assert len(bm25_2.corpus["user_alice"]) == 2

        # Verify query on restored index
        res = bm25_2.query("Newton mechanics", n_results=1, user_id="user_alice")
        assert len(res) == 1
        assert "physics.pdf" in res[0]["metadata"]["source"]


def test_rag_retriever_rehydrates_from_chroma():
    retriever = RAGRetriever.__new__(RAGRetriever)
    mock_chroma = MagicMock()
    mock_chroma.collection.get.return_value = {
        "documents": ["Thermodynamics entropy increases in isolated systems."],
        "metadatas": [{"source": "thermo.pdf", "user_id": "user_bob"}],
    }
    retriever.chroma = mock_chroma

    with tempfile.TemporaryDirectory() as tmpdir:
        disk_path = os.path.join(tmpdir, "bm25_rehydrate.json")
        retriever.bm25 = BM25Index(persistence_path=disk_path)

        # Before rehydration: BM25 is empty
        assert "user_bob" not in retriever.bm25.corpus

        # Run rehydration
        retriever.rehydrate_bm25_from_chroma()

        # After rehydration: BM25 has user_bob's documents
        assert "user_bob" in retriever.bm25.corpus
        assert len(retriever.bm25.corpus["user_bob"]) == 1

        # Query works on rehydrated index
        res = retriever.bm25.query("entropy", user_id="user_bob")
        assert len(res) == 1
        assert res[0]["metadata"]["source"] == "thermo.pdf"
