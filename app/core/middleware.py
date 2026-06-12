import logging
import time
import uuid

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.log_context import set_request_id, set_trace_id
from app.core.metrics import http_request_duration_seconds, http_requests_total

logger = logging.getLogger("fastauth.access")

_ZERO_TRACE_ID = "0" * 32
_SLOW_REQUEST_THRESHOLD_MS = 1000


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        status = str(response.status_code)
        http_requests_total.labels(method=method, path=path, status_code=status).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
        return response


class LoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        status = 500

        span = trace.get_current_span()
        raw_trace_id = format(span.get_span_context().trace_id, "032x")
        trace_id = raw_trace_id if raw_trace_id != _ZERO_TRACE_ID else None
        set_trace_id(trace_id)

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "http",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "content_length": None,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        extra = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_length": response.headers.get("content-length"),
        }

        if duration_ms >= _SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "slow request",
                extra={**extra, "threshold_ms": _SLOW_REQUEST_THRESHOLD_MS},
            )

        if status >= 500:
            logger.error("http", extra=extra)
        elif status >= 400:
            logger.warning("http", extra=extra)
        else:
            logger.info("http", extra=extra)

        return response
