import os
import re
import json
import math
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Lightweight English stop words to filter out pure noise
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
}


def tokenize_text(text: str) -> List[str]:
    """Tokenize and normalize text preserving technical formulas, acronyms, and alphanumeric terms."""
    # Split on whitespace and non-alphanumeric except hyphen or underscore
    tokens = re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


class BM25Index:
    """
    In-memory BM25Okapi inverted index partitioned by tenant (user_id).
    Parameters: k1 = 1.5, b = 0.75
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75, persistence_path: Optional[str] = None):
        self.k1 = k1
        self.b = b
        self.persistence_path = persistence_path or os.environ.get("BM25_PERSISTENCE_PATH", "./data/bm25_index.json")
        # tenant_id -> list of document records
        self.corpus: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.doc_freqs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.inverted_index: Dict[str, Dict[str, List[Tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
        self.total_tokens: Dict[str, int] = defaultdict(int)

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        user_id: str,
        auto_save: bool = True,
    ):
        if not user_id or not str(user_id).strip():
            raise ValueError("user_id is required to index documents in BM25Index")

        tenant = str(user_id)
        start_idx = len(self.corpus[tenant])

        for i, text in enumerate(documents):
            doc_idx = start_idx + i
            meta = metadatas[i] if i < len(metadatas) else {}
            tokens = tokenize_text(text)
            doc_len = len(tokens)

            self.corpus[tenant].append({
                "id": meta.get("id", f"{doc_idx}"),
                "content": text,
                "metadata": dict(meta),
                "tokens": tokens,
                "length": doc_len,
            })
            self.total_tokens[tenant] += doc_len

            term_counts = Counter(tokens)
            for term, count in term_counts.items():
                self.doc_freqs[tenant][term] += 1
                self.inverted_index[tenant][term].append((doc_idx, count))

        if auto_save:
            self.save_to_disk()
    def delete_by_source(self, source: str, user_id: str, auto_save: bool = True):
        if not user_id:
            raise ValueError("user_id is required to delete documents from BM25Index")
        tenant = str(user_id)
        if tenant not in self.corpus:
            return

        # Filter out records matching source
        new_docs = []
        new_metas = []
        for doc in self.corpus[tenant]:
            if doc["metadata"].get("source") != source:
                new_docs.append(doc["content"])
                new_metas.append(doc["metadata"])

        # Rebuild tenant index
        self.clear_tenant(tenant)
        if new_docs:
            self.add_documents(new_docs, new_metas, user_id=tenant, auto_save=False)
        if auto_save:
            self.save_to_disk()

    def save_to_disk(self, file_path: Optional[str] = None) -> bool:
        path = Path(file_path or self.persistence_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {}
            for tenant, docs in self.corpus.items():
                serializable[tenant] = [
                    {"content": d["content"], "metadata": d["metadata"]}
                    for d in docs
                ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning(f"Failed to persist BM25 index to {path}: {e}")
            return False

    def load_from_disk(self, file_path: Optional[str] = None) -> bool:
        path = Path(file_path or self.persistence_path)
        if not path.exists():
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.corpus.clear()
            self.doc_freqs.clear()
            self.inverted_index.clear()
            self.total_tokens.clear()
            for tenant, docs in data.items():
                contents = [d["content"] for d in docs]
                metas = [d.get("metadata", {}) for d in docs]
                self.add_documents(contents, metas, user_id=tenant, auto_save=False)
            logger.info(f"Loaded BM25 index from {path} ({sum(len(d) for d in data.values())} chunks).")
            return True
        except Exception as e:
            logger.warning(f"Failed to load BM25 index from {path}: {e}")
            return False
    def clear_tenant(self, user_id: str):
        tenant = str(user_id)
        if tenant in self.corpus:
            del self.corpus[tenant]
        if tenant in self.doc_freqs:
            del self.doc_freqs[tenant]
        if tenant in self.inverted_index:
            del self.inverted_index[tenant]
        if tenant in self.total_tokens:
            del self.total_tokens[tenant]

    def query(self, query_text: str, n_results: int = 5, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not user_id or not str(user_id).strip():
            raise ValueError("user_id is required for BM25 queries")

        tenant = str(user_id)
        docs = self.corpus.get(tenant, [])
        num_docs = len(docs)
        if num_docs == 0:
            return []

        avgdl = self.total_tokens[tenant] / float(num_docs) if num_docs > 0 else 1.0
        q_tokens = tokenize_text(query_text)
        if not q_tokens:
            return []

        doc_scores: Dict[int, float] = defaultdict(float)

        for term in q_tokens:
            df = self.doc_freqs[tenant].get(term, 0)
            if df == 0:
                continue

            # Robertson-Spärck Jones IDF with smoothing
            idf = math.log(((num_docs - df + 0.5) / (df + 0.5)) + 1.0)
            if idf <= 0:
                idf = 0.05

            postings = self.inverted_index[tenant].get(term, [])
            for doc_idx, tf in postings:
                doc_len = docs[doc_idx]["length"]
                # BM25 term saturation formula
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avgdl))
                doc_scores[doc_idx] += idf * (numerator / denominator)

        if not doc_scores:
            return []

        sorted_indices = sorted(doc_scores.keys(), key=lambda idx: doc_scores[idx], reverse=True)[:n_results]

        # Normalize score
        max_score = max(doc_scores.values()) if doc_scores else 1.0

        results: List[Dict[str, Any]] = []
        for idx in sorted_indices:
            raw_score = doc_scores[idx]
            norm_score = round(raw_score / max_score, 4) if max_score > 0 else 0.0
            results.append({
                "content": docs[idx]["content"],
                "metadata": docs[idx]["metadata"],
                "score": norm_score,
                "raw_bm25_score": round(raw_score, 4),
            })

        return results


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
    dense_weight: float = 1.0,
    bm25_weight: float = 1.0,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) combining dense semantic search and BM25 lexical search.
    RRF(d) = (w_dense / (k + rank_dense(d))) + (w_bm25 / (k + rank_bm25(d)))
    """
    scores: Dict[str, float] = defaultdict(float)
    doc_registry: Dict[str, Dict[str, Any]] = {}
    dense_ranks: Dict[str, int] = {}
    bm25_ranks: Dict[str, int] = {}

    def get_doc_key(doc: Dict[str, Any]) -> str:
        meta = doc.get("metadata", {})
        source = meta.get("source", "")
        chunk_idx = meta.get("chunk_index", "")
        if source and chunk_idx != "":
            return f"{source}:{chunk_idx}"
        # Fallback to normalized content prefix
        content = doc.get("content", "").strip()
        return content[:80]

    for rank, doc in enumerate(dense_results, start=1):
        key = get_doc_key(doc)
        dense_ranks[key] = rank
        scores[key] += dense_weight * (1.0 / (k + rank))
        if key not in doc_registry:
            doc_registry[key] = doc

    for rank, doc in enumerate(bm25_results, start=1):
        key = get_doc_key(doc)
        bm25_ranks[key] = rank
        scores[key] += bm25_weight * (1.0 / (k + rank))
        if key not in doc_registry:
            doc_registry[key] = doc

    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]

    max_rrf = max(scores.values()) if scores else 1.0

    fused_results: List[Dict[str, Any]] = []
    for key in sorted_keys:
        item = dict(doc_registry[key])
        raw_rrf = scores[key]
        normalized_score = round(raw_rrf / max_rrf, 4) if max_rrf > 0 else 0.0

        meta = dict(item.get("metadata", {}))
        meta["dense_rank"] = dense_ranks.get(key)
        meta["bm25_rank"] = bm25_ranks.get(key)
        meta["rrf_score"] = round(raw_rrf, 6)

        item["metadata"] = meta
        item["score"] = normalized_score
        fused_results.append(item)

    return fused_results
