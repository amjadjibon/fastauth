import logging
import traceback
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return appropriate responses."""

    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle exceptions during request processing."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle different types of exceptions."""
        # Get request ID if available
        request_id = getattr(request.state, "request_id", "unknown")

        # Log the exception
        logger.error(
            f"Exception in request {request_id}: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
        )

        # Handle database errors
        if isinstance(exc, SQLAlchemyError):
            return await self._handle_database_error(request_id, exc)

        # Handle validation errors
        if hasattr(exc, "detail") and hasattr(exc, "status_code"):
            return await self._handle_http_exception(request_id, exc)

        # Handle general exceptions
        return await self._handle_general_exception(request_id, exc)

    async def _handle_database_error(
        self, request_id: str, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle database-related errors."""
        error_response = {
            "error": "Database error",
            "message": "A database error occurred. Please try again later.",
            "request_id": request_id,
        }

        if self.debug:
            error_response["detail"] = str(exc)

        return JSONResponse(status_code=500, content=error_response)

    async def _handle_http_exception(self, request_id: str, exc) -> JSONResponse:
        """Handle HTTP exceptions (FastAPI HTTPException)."""
        error_response = {
            "error": "Request error",
            "message": exc.detail if hasattr(exc, "detail") else str(exc),
            "request_id": request_id,
        }

        status_code = getattr(exc, "status_code", 400)

        return JSONResponse(status_code=status_code, content=error_response)

    async def _handle_general_exception(
        self, request_id: str, exc: Exception
    ) -> JSONResponse:
        """Handle general exceptions."""
        error_response = {
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        }

        if self.debug:
            error_response.update(
                {
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

        return JSONResponse(status_code=500, content=error_response)
