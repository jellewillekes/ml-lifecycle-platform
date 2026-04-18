"""JSON logging for the serving API and job families.

Emits Cloud Logging special fields (``severity``,
``logging.googleapis.com/trace``, ``.../spanId``, ``.../trace_sampled``) so
log lines stay linked to OTel traces in Cloud Logging Explorer.
"""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from typing import Any

from opentelemetry import trace

_LOG_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("mlp_log_context", default={})

# Standard LogRecord attributes we don't want to double-emit in `extra`.
_RESERVED = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

_LEVEL_TO_SEVERITY = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class JsonFormatter(logging.Formatter):
    """Format records as single-line JSON with Cloud Logging fields."""

    def __init__(self, service: str, project_id: str | None = None) -> None:
        super().__init__()
        self._service = service
        self._project_id = project_id

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "severity": _LEVEL_TO_SEVERITY.get(record.levelno, record.levelname),
            "message": record.getMessage(),
            "logger": record.name,
            "service": self._service,
        }

        # Context vars set by middleware (request_id) or job entrypoints
        # (job_name, run_id) are attached to every record in scope.
        for key, value in _LOG_CONTEXT.get().items():
            payload.setdefault(key, value)

        # `extra=` fields on the LogRecord.
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload.setdefault(key, value)

        span = trace.get_current_span()
        ctx = span.get_span_context() if span is not None else None
        if ctx is not None and ctx.is_valid:
            trace_id = format(ctx.trace_id, "032x")
            span_id = format(ctx.span_id, "016x")
            if self._project_id:
                payload["logging.googleapis.com/trace"] = (
                    f"projects/{self._project_id}/traces/{trace_id}"
                )
            else:
                payload["logging.googleapis.com/trace"] = trace_id
            payload["logging.googleapis.com/spanId"] = span_id
            payload["logging.googleapis.com/trace_sampled"] = bool(
                ctx.trace_flags.sampled
            )

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(service: str, level: int | str = logging.INFO) -> None:
    """Install the JSON formatter on the root logger.

    Safe to call multiple times; replaces prior handlers installed by this
    function so repeated entrypoint calls don't stack handlers.
    """

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or None

    root = logging.getLogger()
    root.setLevel(level)

    # Drop handlers we installed before; leave foreign handlers alone.
    for handler in list(root.handlers):
        if getattr(handler, "_mlp_json", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service=service, project_id=project_id))
    handler._mlp_json = True  # type: ignore[attr-defined]
    root.addHandler(handler)


def bind_log_context(**fields: Any) -> None:
    """Merge ``fields`` into the ambient log context for the current task."""

    current = dict(_LOG_CONTEXT.get())
    current.update({k: v for k, v in fields.items() if v is not None})
    _LOG_CONTEXT.set(current)


def clear_log_context() -> None:
    _LOG_CONTEXT.set({})
