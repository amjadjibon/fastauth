import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""

    def __init__(
        self,
        app,
        log_level: int = logging.INFO,
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.log_level = log_level
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Get request ID if available
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        logger.log(
            self.log_level,
            f"Request started - {request.method} {request.url.path} "
            f"[ID: {request_id}] [IP: {client_ip}]"
        )

        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.log(
            self.log_level,
            f"Request completed - {request.method} {request.url.path} "
            f"[ID: {request_id}] [Status: {response.status_code}] "
            f"[Time: {process_time:.3f}s]"
        )
        
        # Add process time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
