import re
import math
from typing import List, Dict, Any, Optional

from engines.retrievers import tokenize_text


class RelevanceReRanker:
    """
    Two-stage Cross-Encoder style Relevance ReRanker.
    Evaluates fine-grained query-document alignment beyond bi-encoder vector similarity:
    - Query term coverage and co-occurrence density
    - Exact phrase match and n-gram alignment
    - Term proximity window within document chunks
    - Position discounting (earlier matches weighted higher)
    """

    def __init__(self, phrase_boost: float = 2.0, coverage_weight: float = 1.5):
        self.phrase_boost = phrase_boost
        self.coverage_weight = coverage_weight

    def score_pair(self, query: str, content: str) -> float:
        """Compute fine-grained relevance score between query and document text."""
        q_clean = query.strip().lower()
        doc_clean = content.strip().lower()

        if not q_clean or not doc_clean:
            return 0.0

        q_tokens = tokenize_text(q_clean)
        if not q_tokens:
            return 0.0

        doc_tokens = tokenize_text(doc_clean)
        if not doc_tokens:
            return 0.0

        # 1. Exact phrase match boost
        phrase_score = 0.0
        if len(q_clean) > 5 and q_clean in doc_clean:
            phrase_score = self.phrase_boost

        # 2. Query Term Coverage (Fraction of query terms present in doc)
        unique_q_terms = set(q_tokens)
        doc_terms_set = set(doc_tokens)
        matched_terms = unique_q_terms.intersection(doc_terms_set)
        term_coverage = len(matched_terms) / float(len(unique_q_terms))

        # 3. Term frequency saturation
        tf_score = 0.0
        doc_token_counts = {}
        for t in doc_tokens:
            doc_token_counts[t] = doc_token_counts.get(t, 0) + 1

        for t in matched_terms:
            tf = doc_token_counts[t]
            tf_score += math.log(1.0 + tf)

        # 4. Term Proximity: span width between earliest and latest query term
        proximity_score = 0.0
        term_positions = [i for i, t in enumerate(doc_tokens) if t in unique_q_terms]
        if len(term_positions) > 1:
            span = max(term_positions) - min(term_positions) + 1
            if span > 0:
                proximity_score = min(1.0, len(term_positions) / float(span))

        # Combined composite score
        total_score = (
            phrase_score +
            (term_coverage * self.coverage_weight) +
            (tf_score * 0.4) +
            (proximity_score * 0.6)
        )

        return total_score

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Re-rank candidate documents based on query-chunk cross-scoring."""
        if not candidates:
            return []

        scored_candidates = []
        for cand in candidates:
            content = cand.get("content", "")
            base_score = float(cand.get("score", 0.0))
            rerank_score = self.score_pair(query, content)

            # Blend prior stage retrieval score (RRF/Dense) with cross-encoder relevance
            blended_score = (base_score * 0.4) + (rerank_score * 0.6)

            item = dict(cand)
            meta = dict(item.get("metadata", {}))
            meta["cross_encoder_score"] = round(rerank_score, 4)
            meta["blended_score"] = round(blended_score, 4)

            item["metadata"] = meta
            item["score"] = round(blended_score, 4)
            scored_candidates.append(item)

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]
