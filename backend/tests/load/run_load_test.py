import asyncio
import time
from typing import Dict, Any, List
import httpx


async def _worker(
    worker_id: int,
    base_url: str,
    requests_per_worker: int,
    latencies: List[float],
    status_counts: Dict[int, int],
):
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for _ in range(requests_per_worker):
            t0 = time.perf_counter()
            try:
                res = await client.get("/health/live")
                dur_ms = (time.perf_counter() - t0) * 1000
                latencies.append(dur_ms)
                status_counts[res.status_code] = status_counts.get(res.status_code, 0) + 1
            except Exception:
                status_counts[500] = status_counts.get(500, 0) + 1


async def run_async_load_test(
    base_url: str = "http://127.0.0.1:8000",
    concurrency: int = 10,
    requests_per_worker: int = 20,
) -> Dict[str, Any]:
    latencies: List[float] = []
    status_counts: Dict[int, int] = {}

    t_start = time.perf_counter()
    tasks = [
        _worker(i, base_url, requests_per_worker, latencies, status_counts)
        for i in range(concurrency)
    ]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    total_requests = len(latencies)
    latencies.sort()

    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0

    rps = total_requests / total_time if total_time > 0 else 0.0
    success_count = status_counts.get(200, 0)
    success_rate = (success_count / total_requests) if total_requests > 0 else 0.0

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "total_time_seconds": round(total_time, 3),
        "requests_per_second": round(rps, 2),
        "success_rate": round(success_rate, 4),
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "p99_latency_ms": round(p99, 2),
        "status_distribution": status_counts,
    }


if __name__ == "__main__":
    import json
    report = asyncio.run(run_async_load_test(concurrency=5, requests_per_worker=10))
    print(json.dumps(report, indent=2))
