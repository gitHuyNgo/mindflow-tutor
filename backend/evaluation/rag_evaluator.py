import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class RAGTestCase:
    query: str
    tenant_id: str
    expected_sources: List[str]
    expected_keywords: List[str] = field(default_factory=list)
    cross_tenant_probe: bool = False  # If True, expected_sources belong to another tenant


@dataclass
class RAGEvaluationReport:
    total_queries: int
    hit_rate_at_3: float
    hit_rate_at_5: float
    mrr: float
    precision_at_3: float
    tenant_leak_count: int
    tenant_leak_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    detailed_results: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "hit_rate@3": round(self.hit_rate_at_3, 4),
            "hit_rate@5": round(self.hit_rate_at_5, 4),
            "mrr": round(self.mrr, 4),
            "precision@3": round(self.precision_at_3, 4),
            "tenant_leak_rate": round(self.tenant_leak_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
        }


class RAGEvaluator:
    """Quantitative evaluation suite for RAG retrieval and multi-tenancy isolation."""

    def __init__(self, retriever_fn=None):
        self.retriever_fn = retriever_fn

    def evaluate(self, test_cases: List[RAGTestCase]) -> RAGEvaluationReport:
        if not test_cases:
            return RAGEvaluationReport(
                total_queries=0,
                hit_rate_at_3=0.0,
                hit_rate_at_5=0.0,
                mrr=0.0,
                precision_at_3=0.0,
                tenant_leak_count=0,
                tenant_leak_rate=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
            )

        hits_at_3 = 0
        hits_at_5 = 0
        reciprocal_ranks = []
        precisions_at_3 = []
        tenant_leaks = 0
        latencies = []
        details = []

        for tc in test_cases:
            t0 = time.perf_counter()
            if self.retriever_fn:
                raw_results = self.retriever_fn(tc.query, user_id=tc.tenant_id, n_results=5)
            else:
                raw_results = {"results": []}
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)

            retrieved = raw_results.get("results", [])
            retrieved_sources = [r.get("metadata", {}).get("source", "") for r in retrieved]
            retrieved_tenants = [r.get("metadata", {}).get("user_id", "") for r in retrieved]

            # Check for tenant leakage (chunks belonging to someone else)
            leaked = any(t and t != tc.tenant_id for t in retrieved_tenants)
            if leaked:
                tenant_leaks += 1

            if tc.cross_tenant_probe:
                # In cross-tenant probe, success means NO foreign docs retrieved
                details.append({
                    "query": tc.query,
                    "tenant_id": tc.tenant_id,
                    "cross_tenant_probe": True,
                    "leaked": leaked,
                    "latency_ms": elapsed_ms,
                })
                continue

            # Standard Hit Rate & MRR computation
            rank_found = None
            relevant_in_top3 = 0

            for i, src in enumerate(retrieved_sources[:5]):
                is_match = any(exp.lower() in src.lower() for exp in tc.expected_sources)
                if is_match:
                    if rank_found is None:
                        rank_found = i + 1
                    if i < 3:
                        relevant_in_top3 += 1

            if rank_found and rank_found <= 3:
                hits_at_3 += 1
            if rank_found and rank_found <= 5:
                hits_at_5 += 1

            reciprocal_ranks.append(1.0 / rank_found if rank_found else 0.0)
            precisions_at_3.append(relevant_in_top3 / 3.0)

            details.append({
                "query": tc.query,
                "tenant_id": tc.tenant_id,
                "expected": tc.expected_sources,
                "retrieved": retrieved_sources,
                "rank": rank_found,
                "latency_ms": elapsed_ms,
            })

        total = len([tc for tc in test_cases if not tc.cross_tenant_probe]) or 1
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)

        return RAGEvaluationReport(
            total_queries=len(test_cases),
            hit_rate_at_3=hits_at_3 / total,
            hit_rate_at_5=hits_at_5 / total,
            mrr=sum(reciprocal_ranks) / total if reciprocal_ranks else 0.0,
            precision_at_3=sum(precisions_at_3) / total if precisions_at_3 else 0.0,
            tenant_leak_count=tenant_leaks,
            tenant_leak_rate=tenant_leaks / len(test_cases),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
            p95_latency_ms=latencies[p95_idx] if latencies else 0.0,
            detailed_results=details,
        )
