import pytest
from engines.chunking import baseline_chunk_text, split_text_recursive, markdown_chunk_text
from engines.retrievers import BM25Index, reciprocal_rank_fusion, tokenize_text
from engines.reranker import RelevanceReRanker
from engines.rag_retriever import RAGRetriever
from evaluation.rag_metrics import (
    calculate_recall_at_k,
    calculate_precision_at_k,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_answer_correctness,
    calculate_citation_groundedness,
    is_correct_refusal,
)
from evaluation.datasets.golden_dataset import build_golden_dataset
from evaluation.compare_rag_configs import run_comprehensive_rag_benchmark, generate_markdown_report


def test_recursive_chunking_bounds_oversized_paragraphs():
    # Construct a single continuous paragraph of 3,200 characters without any \n\n
    sentence = "Newton's laws of motion define the relationship between forces and bodies. "
    oversized_para = sentence * 45  # ~3375 chars
    assert len(oversized_para) > 3000

    # 1. Baseline chunker overflows
    legacy_chunks = baseline_chunk_text(oversized_para, chunk_size=800, overlap=120)
    assert any(len(c) > 800 for c in legacy_chunks), "Baseline chunker should demonstrate the overflow bug"

    # 2. Improved recursive chunker strictly bounds all chunks
    improved_chunks = split_text_recursive(oversized_para, chunk_size=800, chunk_overlap=120)
    assert len(improved_chunks) > 1
    for chunk in improved_chunks:
        assert len(chunk) <= 800, f"Chunk exceeded maximum chunk_size 800: {len(chunk)}"


def test_markdown_chunking_preserves_breadcrumbs():
    markdown_doc = """# Physics Mechanics
## Kinematics
Linear motion describes movement along a straight line in one dimension.
### Constant Acceleration
Equations of motion under constant acceleration include v = v_0 + a*t.
"""
    chunks = markdown_chunk_text(markdown_doc, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert "Physics Mechanics" in first_chunk["breadcrumb"]
    assert first_chunk["length"] <= 500


def test_bm25_retrieval_and_tenant_isolation():
    bm25 = BM25Index()
    user_a_docs = [
        "Newton's second law is F = ma, where force equals mass times acceleration.",
        "Photosynthesis converts light energy into chemical energy in plants.",
    ]
    user_a_metas = [{"source": "physics.pdf"}, {"source": "biology.pdf"}]
    bm25.add_documents(user_a_docs, user_a_metas, user_id="user_a")

    user_b_docs = [
        "Quantum superposition allows particles to exist in multiple states.",
    ]
    user_b_metas = [{"source": "quantum.pdf"}]
    bm25.add_documents(user_b_docs, user_b_metas, user_id="user_b")

    # User A queries for F = ma
    res_a = bm25.query("Newton's second law F = ma", n_results=2, user_id="user_a")
    assert len(res_a) >= 1
    assert "physics.pdf" in res_a[0]["metadata"]["source"]
    assert res_a[0]["score"] > 0.0

    # User A should NOT see User B's documents
    assert all("quantum.pdf" not in r["metadata"].get("source", "") for r in res_a)

    # Empty / wrong user returns empty
    res_unknown = bm25.query("Newton", n_results=2, user_id="user_unknown")
    assert res_unknown == []


def test_reciprocal_rank_fusion():
    dense_results = [
        {"content": "Doc A: Physics", "metadata": {"source": "docA.pdf", "chunk_index": 0}, "score": 0.95},
        {"content": "Doc B: Biology", "metadata": {"source": "docB.pdf", "chunk_index": 0}, "score": 0.85},
    ]
    bm25_results = [
        {"content": "Doc B: Biology", "metadata": {"source": "docB.pdf", "chunk_index": 0}, "score": 1.0},
        {"content": "Doc C: Chemistry", "metadata": {"source": "docC.pdf", "chunk_index": 0}, "score": 0.70},
    ]

    fused = reciprocal_rank_fusion(dense_results, bm25_results, k=60, top_n=3)
    assert len(fused) == 3
    # Doc B appeared in both lists, so its RRF rank score should be highest
    assert fused[0]["metadata"]["source"] == "docB.pdf"
    assert "rrf_score" in fused[0]["metadata"]


def test_relevance_reranker():
    reranker = RelevanceReRanker()
    query = "Newton's second law acceleration"
    candidates = [
        {"content": "General introduction to science and laboratory equipment.", "score": 0.80},
        {"content": "Newton's second law states that acceleration is proportional to net force.", "score": 0.60},
    ]

    reranked = reranker.rerank(query, candidates, top_k=2)
    assert len(reranked) == 2
    # The candidate with exact query terms and term coverage should be ranked first
    assert "Newton's second law" in reranked[0]["content"]
    assert "cross_encoder_score" in reranked[0]["metadata"]


def test_rag_retriever_retrieval_modes():
    retriever = RAGRetriever.__new__(RAGRetriever)
    from unittest.mock import MagicMock
    mock_chroma = MagicMock()
    mock_chroma.query.return_value = {
        "documents": [["Dense Chunk Content"]],
        "metadatas": [[{"source": "dense.pdf", "chunk_index": 1}]],
        "distances": [[0.15]],
    }
    retriever.chroma = mock_chroma
    retriever.bm25 = BM25Index()
    retriever.bm25.add_documents(
        ["BM25 Lexical Chunk Content"],
        [{"source": "bm25.pdf", "chunk_index": 1}],
        user_id="user_test",
    )
    retriever.reranker = RelevanceReRanker()

    # Dense mode
    res_dense = retriever.retrieve("query", user_id="user_test", mode="dense")
    assert res_dense["mode"] == "dense"
    assert len(res_dense["results"]) == 1

    # BM25 mode
    res_bm25 = retriever.retrieve("BM25", user_id="user_test", mode="bm25")
    assert res_bm25["mode"] == "bm25"
    assert len(res_bm25["results"]) == 1

    # Hybrid mode
    res_hybrid = retriever.retrieve("Content", user_id="user_test", mode="hybrid")
    assert res_hybrid["mode"] == "hybrid"
    assert len(res_hybrid["results"]) >= 1

    # No RAG mode
    res_none = retriever.retrieve("Content", user_id="user_test", mode="no_rag")
    assert res_none["mode"] == "no_rag"
    assert len(res_none["results"]) == 0


def test_rag_metrics():
    retrieved = ["physics_mechanics.pdf", "biology.pdf", "chemistry.pdf"]
    expected = ["physics_mechanics.pdf"]

    recall = calculate_recall_at_k(retrieved, expected, k=3)
    assert recall == 1.0

    precision = calculate_precision_at_k(retrieved, expected, k=3)
    assert round(precision, 2) == 0.33

    mrr = calculate_mrr(retrieved, expected)
    assert mrr == 1.0  # Found at rank 1

    ndcg = calculate_ndcg_at_k(retrieved, expected, k=3)
    assert ndcg == 1.0

    # Groundedness test
    context = "Newton's second law is F = ma. Acceleration is proportional to net force."
    grounded_ans = "Newton's second law states that F = ma and acceleration is proportional to net force."
    score = calculate_citation_groundedness(grounded_ans, context)
    assert score >= 0.80

    # Refusal test
    assert is_correct_refusal("This topic is not mentioned in the provided study documents.") is True
    assert is_correct_refusal("The answer is 42 and it works via quantum fluctuations.") is False


def test_golden_dataset_structure():
    dataset = build_golden_dataset()
    assert len(dataset) >= 100
    answerable = [q for q in dataset if q.is_answerable]
    unanswerable = [q for q in dataset if not q.is_answerable]

    assert len(answerable) >= 80
    assert len(unanswerable) >= 20

    # Every item must have query and answer
    for q in dataset:
        assert q.id
        assert q.query
        assert q.ground_truth_answer
        assert q.domain


def test_comprehensive_benchmark_runner():
    report = run_comprehensive_rag_benchmark()
    assert "configurations" in report
    assert len(report["configurations"]) == 6
    assert "key_findings" in report

    md = generate_markdown_report(report)
    assert "# 📊 Evaluated RAG Benchmark Report" in md
    assert "Improved Chunking + Hybrid + Reranking" in md
