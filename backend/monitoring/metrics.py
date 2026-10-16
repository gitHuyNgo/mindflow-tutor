import time
import uuid
import threading
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_lock = threading.Lock()

# Metric stores
_http_requests_total: Dict[Tuple[str, str, int], int] = {}
_http_request_duration_seconds: Dict[Tuple[str, str], List[float]] = {}
_active_sessions_count: int = 0
_ai_tokens_total: Dict[Tuple[str, str, str], int] = {}
_ai_latency_seconds: Dict[Tuple[str, str], List[float]] = {}
_rag_queries_total: Dict[str, int] = {}
_rag_duration_seconds: List[float] = []


def record_http_request(method: str, endpoint: str, status_code: int, duration_s: float):
    with _lock:
        key = (method, endpoint, status_code)
        _http_requests_total[key] = _http_requests_total.get(key, 0) + 1

        dur_key = (method, endpoint)
        if dur_key not in _http_request_duration_seconds:
            _http_request_duration_seconds[dur_key] = []
        _http_request_duration_seconds[dur_key].append(duration_s)
        # Keep window bounded to latest 1000 observations per route
        if len(_http_request_duration_seconds[dur_key]) > 1000:
            _http_request_duration_seconds[dur_key] = _http_request_duration_seconds[dur_key][-1000:]


def set_active_sessions(count: int):
    global _active_sessions_count
    with _lock:
        _active_sessions_count = count


def record_ai_usage(provider: str, model: str, token_type: str, token_count: int, latency_s: float = 0.0):
    with _lock:
        key = (provider, model, token_type)
        _ai_tokens_total[key] = _ai_tokens_total.get(key, 0) + token_count

        if latency_s > 0:
            lat_key = (provider, model)
            if lat_key not in _ai_latency_seconds:
                _ai_latency_seconds[lat_key] = []
            _ai_latency_seconds[lat_key].append(latency_s)
            if len(_ai_latency_seconds[lat_key]) > 1000:
                _ai_latency_seconds[lat_key] = _ai_latency_seconds[lat_key][-1000:]


def record_rag_query(status: str, duration_s: float):
    with _lock:
        _rag_queries_total[status] = _rag_queries_total.get(status, 0) + 1
        _rag_duration_seconds.append(duration_s)
        if len(_rag_duration_seconds) > 1000:
            _rag_duration_seconds.pop(0)


def export_prometheus_text() -> str:
    """Generate standard Prometheus / OpenMetrics 0.0.4 text export."""
    lines: List[str] = [
        "# HELP http_requests_total Total number of HTTP requests processed.",
        "# TYPE http_requests_total counter",
    ]
    with _lock:
        for (method, endpoint, status), count in _http_requests_total.items():
            lines.append(f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}')

        lines.extend([
            "# HELP http_request_duration_seconds HTTP request latency summary in seconds.",
            "# TYPE http_request_duration_seconds gauge",
        ])
        for (method, endpoint), durs in _http_request_duration_seconds.items():
            if durs:
                avg_dur = sum(durs) / len(durs)
                lines.append(f'http_request_duration_seconds{{method="{method}",endpoint="{endpoint}",metric="avg"}} {avg_dur:.4f}')

        lines.extend([
            "# HELP active_sessions_count Current count of active user study sessions.",
            "# TYPE active_sessions_count gauge",
            f"active_sessions_count {_active_sessions_count}",
        ])

        lines.extend([
            "# HELP ai_tokens_total Cumulative AI tokens consumed by model and type.",
            "# TYPE ai_tokens_total counter",
        ])
        for (provider, model, ttype), count in _ai_tokens_total.items():
            lines.append(f'ai_tokens_total{{provider="{provider}",model="{model}",type="{ttype}"}} {count}')

        lines.extend([
            "# HELP rag_queries_total Total RAG document retrieval queries executed.",
            "# TYPE rag_queries_total counter",
        ])
        for status, count in _rag_queries_total.items():
            lines.append(f'rag_queries_total{{status="{status}"}} {count}')

    return "\n".join(lines) + "\n"


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for request timing, correlation IDs, and Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        t0 = time.perf_counter()

        response: Response = await call_next(request)

        duration_s = time.perf_counter() - t0
        duration_ms = duration_s * 1000

        # Attach standard observability headers
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        # Record metrics (skip metrics scraping endpoint itself to prevent metric inflation)
        path = request.url.path
        if path != "/metrics":
            record_http_request(request.method, path, response.status_code, duration_s)

        return response
