from unittest.mock import MagicMock
from persistence.chroma_store import ChromaStore


def test_chroma_store_add_documents_injects_user_id():
    """Verify add_documents enriches metadata with user_id."""
    store = ChromaStore.__new__(ChromaStore)
    mock_collection = MagicMock()
    store.collection = mock_collection

    docs = ["Page 1 text", "Page 2 text"]
    metas = [{"source": "physics.pdf", "page": 1}, {"source": "physics.pdf", "page": 2}]

    store.add_documents(docs, metas, user_id="student_alice")

    mock_collection.add.assert_called_once()
    _, kwargs = mock_collection.add.call_args
    passed_metas = kwargs["metadatas"]

    assert len(passed_metas) == 2
    assert passed_metas[0]["user_id"] == "student_alice"
    assert passed_metas[1]["user_id"] == "student_alice"
    assert passed_metas[0]["source"] == "physics.pdf"


def test_chroma_store_query_enforces_user_tenant():
    """Verify query filters by where={'user_id': user_id}."""
    store = ChromaStore.__new__(ChromaStore)
    mock_collection = MagicMock()
    mock_collection.count.return_value = 10
    mock_collection.get.return_value = {"ids": ["doc_1", "doc_2"]}
    mock_collection.query.return_value = {
        "documents": [["Alice's notes"]],
        "metadatas": [[{"user_id": "student_alice"}]],
        "distances": [[0.1]],
    }
    store.collection = mock_collection

    store.query("kinematics", n_results=3, user_id="student_alice")

    mock_collection.query.assert_called_once()
    _, kwargs = mock_collection.query.call_args
    assert kwargs["where"] == {"user_id": "student_alice"}
    assert kwargs["n_results"] == 2


def test_chroma_store_query_empty_tenant_returns_empty():
    """If a tenant has no documents, query must return empty without querying other users."""
    store = ChromaStore.__new__(ChromaStore)
    mock_collection = MagicMock()
    mock_collection.count.return_value = 10
    # No documents for Bob
    mock_collection.get.return_value = {"ids": []}
    store.collection = mock_collection

    res = store.query("kinematics", n_results=3, user_id="student_bob")

    # Should short-circuit and NOT call collection.query
    mock_collection.query.assert_not_called()
    assert res == {"documents": [[]], "metadatas": [[]], "distances": [[]]}


def test_chroma_store_delete_by_source_scoped_to_user():
    """Verify delete_by_source only deletes the specific user's document chunks."""
    store = ChromaStore.__new__(ChromaStore)
    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": ["chunk_1", "chunk_2"]}
    store.collection = mock_collection

    store.delete_by_source("biology.pdf", user_id="student_alice")

    mock_collection.get.assert_called_once_with(
        where={"$and": [{"source": "biology.pdf"}, {"user_id": "student_alice"}]},
        include=["metadatas"],
    )
    mock_collection.delete.assert_called_once_with(ids=["chunk_1", "chunk_2"])

def test_chroma_store_operations_reject_missing_user_id():
    """Verify that omitting user_id raises ValueError across all ChromaStore operations."""
    import pytest
    store = ChromaStore.__new__(ChromaStore)
    mock_collection = MagicMock()
    store.collection = mock_collection

    with pytest.raises(ValueError, match="Tenant user_id is required"):
        store.query("hello", user_id=None)

    with pytest.raises(ValueError, match="Tenant user_id is required"):
        store.add_documents(["doc"], [{}], user_id=None)

    with pytest.raises(ValueError, match="Tenant user_id is required"):
        store.delete_by_source("source.pdf", user_id=None)

    with pytest.raises(ValueError, match="Tenant user_id is required"):
        store.list_sources(user_id=None)

    with pytest.raises(ValueError, match="Tenant user_id is required"):
        store.get_document_count(user_id=None)


def test_rag_retriever_unscoped_calls_safe_fallback():
    """Verify that RAGRetriever safely short-circuits without querying vector store if user_id is None."""
    from engines.rag_retriever import RAGRetriever
    retriever = RAGRetriever.__new__(RAGRetriever)
    mock_chroma = MagicMock()
    retriever.chroma = mock_chroma

    # Unauthenticated retrieve should return empty result
    res = retriever.retrieve("algebra", user_id=None)
    assert res["results"] == []
    assert res["total_found"] == 0
    mock_chroma.query.assert_not_called()

    # Unauthenticated get_context should return safe fallback string
    ctx = retriever.get_context("algebra", user_id=None)
    assert ctx == "No relevant materials found in uploaded documents."
