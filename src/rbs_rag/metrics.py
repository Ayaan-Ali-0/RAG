from __future__ import annotations

import time
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUESTS_TOTAL = Counter(
    "rag_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

REQUESTS_DURATION = Histogram(
    "rag_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

DOCUMENTS_INGESTED = Counter(
    "rag_documents_ingested_total",
    "Total documents ingested",
    labelnames=["tenant_id"],
)

CHUNKS_CREATED = Counter(
    "rag_chunks_created_total",
    "Total chunks created",
    labelnames=["tenant_id"],
)

CHUNKS_RETRIEVED = Histogram(
    "rag_chunks_retrieved_count",
    "Number of chunks retrieved per query",
    buckets=(1, 3, 5, 8, 10, 15, 20, 30, 50),
)

LLM_REQUESTS = Counter(
    "rag_llm_requests_total",
    "Total LLM requests",
    labelnames=["provider", "model"],
)

LLM_DURATION = Histogram(
    "rag_llm_duration_seconds",
    "LLM request duration in seconds",
    labelnames=["provider", "model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
)

PROMPT_INJECTIONS_BLOCKED = Counter(
    "rag_prompt_injections_blocked_total",
    "Total prompt injection attempts blocked",
)

ACTIVE_TENANTS = Gauge(
    "rag_active_tenants",
    "Number of active tenants",
)

ENGINE_UPTIME = Gauge(
    "rag_engine_uptime_seconds",
    "Engine uptime in seconds",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path
        start = time.monotonic()

        response = await call_next(request)

        duration = time.monotonic() - start
        status = str(response.status_code)

        REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUESTS_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return response


def metrics_export():
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")
