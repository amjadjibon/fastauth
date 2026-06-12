import logging
from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_request_id(value: str) -> None:
    _request_id.set(value)


def set_trace_id(value: str | None) -> None:
    _trace_id.set(value)


class RequestContextFilter(logging.Filter):
    """Injects request_id and trace_id from context vars into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = _request_id.get()  # type: ignore[attr-defined]
            record.trace_id = _trace_id.get()  # type: ignore[attr-defined]
        except Exception:
            record.request_id = None  # type: ignore[attr-defined]
            record.trace_id = None  # type: ignore[attr-defined]
        return True
