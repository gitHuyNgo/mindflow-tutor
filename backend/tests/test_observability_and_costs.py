import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.metrics import (
    MetricsMiddleware,
    record_http_request,
    record_ai_usage,
    set_active_sessions,
    export_prometheus_text,
)
from monitoring.cost_tracker import CostTracker
from routers.system import router as system_router

app = FastAPI()
app.add_middleware(MetricsMiddleware)
app.include_router(system_router)
client = TestClient(app)


def test_metrics_middleware_injects_headers():
    res = client.get("/health/live")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert "X-Response-Time-Ms" in res.headers
    float_ms = float(res.headers["X-Response-Time-Ms"])
    assert float_ms >= 0.0


def test_prometheus_metrics_export():
    record_http_request("POST", "/v1/ask", 200, 0.125)
    record_ai_usage("openai", "gpt-4o-mini", "prompt", 1500, 0.45)
    set_active_sessions(42)

    output = export_prometheus_text()
    assert "# TYPE http_requests_total counter" in output
    assert 'http_requests_total{method="POST",endpoint="/v1/ask",status="200"}' in output
    assert "active_sessions_count 42" in output
    assert 'ai_tokens_total{provider="openai",model="gpt-4o-mini",type="prompt"} 1500' in output


def test_health_endpoints():
    # Liveness check
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    # Readiness check with mocked database
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1})
    with patch("routers.system.get_db", return_value=mock_db):
        ready_res = client.get("/health/ready")
        assert ready_res.status_code == 200
        assert ready_res.json()["status"] == "ready"
        assert ready_res.json()["database"] == "connected"


def test_metrics_endpoint():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    assert "# HELP http_requests_total" in res.text


def test_cost_tracker_calculations():
    tracker = CostTracker()
    tracker.record_llm("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    tracker.record_embedding(tokens=1_000_000)
    tracker.record_tts(characters=1_000_000)
    tracker.record_parsing(pages=100)

    # 1M input gpt-4o-mini = $0.150
    # 1M output gpt-4o-mini = $0.600
    # 1M embedding = $0.020
    # 1M tts chars = $15.000
    # 100 pages = $0.300
    # Total expected = 0.15 + 0.60 + 0.02 + 15.00 + 0.30 = 16.07
    total = tracker.calculate_total_cost_usd()
    assert round(total, 2) == 16.07


def test_estimate_session_cost():
    estimate = CostTracker.estimate_session_cost(
        turns=10,
        avg_prompt_tokens=400,
        avg_completion_tokens=200,
        tts_chars_per_turn=300,
        rag_doc_pages=5,
        model="gpt-4o-mini",
    )
    assert estimate["turns"] == 10
    assert estimate["total_session_cost_usd"] > 0.0
    assert estimate["cost_per_100_sessions_usd"] == round(estimate["total_session_cost_usd"] * 100, 3)
