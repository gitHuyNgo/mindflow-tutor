import math
import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field

from engines.retrievers import tokenize_text


def calculate_recall_at_k(retrieved_sources: List[str], expected_sources: List[str], k: int = 5) -> float:
    """Fraction of relevant sources retrieved in top k."""
    if not expected_sources:
        return 1.0
    top_k = retrieved_sources[:k]
    matched = 0
    for exp in expected_sources:
        if any(exp.lower() in s.lower() or s.lower() in exp.lower() for s in top_k):
            matched += 1
    return matched / float(len(expected_sources))


def calculate_precision_at_k(retrieved_sources: List[str], expected_sources: List[str], k: int = 5) -> float:
    """Fraction of retrieved items in top k that are relevant."""
    if k <= 0:
        return 0.0
    top_k = retrieved_sources[:k]
    relevant_count = 0
    for s in top_k:
        if any(exp.lower() in s.lower() or s.lower() in exp.lower() for exp in expected_sources):
            relevant_count += 1
    return relevant_count / float(k)


def calculate_mrr(retrieved_sources: List[str], expected_sources: List[str]) -> float:
    """Mean Reciprocal Rank: 1 / rank of first relevant retrieved document."""
    for rank, s in enumerate(retrieved_sources, start=1):
        if any(exp.lower() in s.lower() or s.lower() in exp.lower() for exp in expected_sources):
            return 1.0 / float(rank)
    return 0.0


def calculate_ndcg_at_k(retrieved_sources: List[str], expected_sources: List[str], k: int = 5) -> float:
    """
    Normalized Discounted Cumulative Gain at rank k.
    Binary relevance: 1 if matches expected source, 0 otherwise.
    Each expected source is rewarded once at its highest rank.
    """
    if not expected_sources or k <= 0:
        return 0.0

    dcg = 0.0
    top_k = retrieved_sources[:k]
    matched_sources = set()

    for i, s in enumerate(top_k, start=1):
        for exp in expected_sources:
            if (exp.lower() in s.lower() or s.lower() in exp.lower()) and exp not in matched_sources:
                matched_sources.add(exp)
                dcg += 1.0 / math.log2(i + 1)
                break

    # Calculate Ideal DCG@k (all relevant items appear at top ranks)
    idcg = 0.0
    ideal_hits = min(len(expected_sources), k)
    for i in range(1, ideal_hits + 1):
        idcg += 1.0 / math.log2(i + 1)

    if idcg <= 0.0:
        return 0.0
    return min(1.0, dcg / idcg)

def calculate_answer_correctness(generated_answer: str, ground_truth_answer: str) -> float:
    """
    Token-level F1 score and key fact overlap between generated answer and ground truth.
    Scale: [0.0, 1.0]
    """
    gen_tokens = tokenize_text(generated_answer)
    gt_tokens = tokenize_text(ground_truth_answer)

    if not gt_tokens:
        return 1.0 if not gen_tokens else 0.5
    if not gen_tokens:
        return 0.0

    gen_set = set(gen_tokens)
    gt_set = set(gt_tokens)

    intersection = gen_set.intersection(gt_set)
    if not intersection:
        return 0.0

    precision = len(intersection) / float(len(gen_set))
    recall = len(intersection) / float(len(gt_set))

    f1 = (2 * precision * recall) / (precision + recall)
    return round(f1, 4)


def calculate_citation_groundedness(generated_answer: str, retrieved_context: str) -> float:
    """
    Measures what fraction of content sentences/claims in the generated answer
    are grounded in the retrieved context chunks (detecting hallucination).
    Scale: [0.0, 1.0] (1.0 = 100% grounded, 0.0 = completely hallucinated).
    """
    if not generated_answer or not generated_answer.strip():
        return 1.0

    # If context is empty or refusal
    if not retrieved_context or "no relevant materials" in retrieved_context.lower():
        refusal_phrases = ["cannot be found", "not mentioned", "no relevant", "do not have information", "not found in"]
        is_honest_refusal = any(p in generated_answer.lower() for p in refusal_phrases)
        return 1.0 if is_honest_refusal else 0.0

    # Split answer into sentence claims
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", generated_answer) if len(s.strip()) > 15]
    if not sentences:
        return 1.0

    context_clean = retrieved_context.lower()
    grounded_count = 0

    for sentence in sentences:
        s_tokens = tokenize_text(sentence)
        if not s_tokens:
            continue
        # Check if significant portion of tokens (>50%) exist in context
        matched = sum(1 for t in s_tokens if t in context_clean)
        coverage = matched / float(len(s_tokens))
        if coverage >= 0.55:
            grounded_count += 1

    return round(grounded_count / float(len(sentences)), 4)


def is_correct_refusal(generated_answer: str) -> bool:
    """Check if model correctly identified that the document does not contain the answer."""
    lower = generated_answer.lower()
    refusal_signals = [
        "no relevant", "not mentioned", "not found", "cannot find", "does not contain",
        "do not contain", "not provided", "no information", "cannot answer"
    ]
    return any(sig in lower for sig in refusal_signals)


@dataclass
class RAGConfigMetrics:
    config_name: str
    total_queries: int
    recall_at_3: float
    recall_at_5: float
    mrr: float
    ndcg_at_5: float
    precision_at_3: float
    answer_correctness: float
    citation_groundedness: float
    unanswerable_refusal_accuracy: float
    avg_latency_ms: float
    p95_latency_ms: float
    estimated_cost_per_1k_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_name": self.config_name,
            "total_queries": self.total_queries,
            "recall@3": round(self.recall_at_3, 4),
            "recall@5": round(self.recall_at_5, 4),
            "mrr": round(self.mrr, 4),
            "ndcg@5": round(self.ndcg_at_5, 4),
            "precision@3": round(self.precision_at_3, 4),
            "answer_correctness": round(self.answer_correctness, 4),
            "citation_groundedness": round(self.citation_groundedness, 4),
            "unanswerable_refusal_accuracy": round(self.unanswerable_refusal_accuracy, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "cost_per_1k_usd": round(self.estimated_cost_per_1k_usd, 4),
        }
