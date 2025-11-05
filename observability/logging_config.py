"""Structured logging with OpenTelemetry trace correlation and PII masking."""

from __future__ import annotations

import logging
import os
import re
import sys
from typing import Any

import structlog
from opentelemetry import trace

_ENV = os.getenv("DEPLOYMENT_ENV", "production")
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_SERVICE_NAME = os.getenv("SERVICE_NAME", "ecosupplyai")

_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL_REDACTED]"),
    (re.compile(r"\+?\d{1,4}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}"), "[PHONE_REDACTED]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CC_REDACTED]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"(?:api[_-]?key|token|secret|password|bearer)\s*[:=]\s*\S+", re.IGNORECASE), "[CREDENTIAL_REDACTED]"),
]


def _add_service_name(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["service"] = _SERVICE_NAME
    return event_dict


def _add_trace_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    else:
        event_dict["trace_id"] = "0" * 32
        event_dict["span_id"] = "0" * 16
    return event_dict


def _mask_pii(obj: Any) -> Any:
    if isinstance(obj, str):
        for pattern, replacement in _PII_PATTERNS:
            obj = pattern.sub(replacement, obj)
        return obj
    elif isinstance(obj, dict):
        return {k: _mask_pii(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_mask_pii(item) for item in obj)
    return obj


def _mask_sensitive_data(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return _mask_pii(event_dict)


_configured = False


def _configure_structlog() -> None:
    global _configured
    if _configured:
        return

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_service_name,
        _add_trace_context,
        _mask_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if _ENV == "production"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer]
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

    for noisy in ("uvicorn.access", "httpcore", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger with trace context and PII masking."""
    _configure_structlog()
    return structlog.get_logger(name)
