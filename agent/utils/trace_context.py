from __future__ import annotations

import contextvars
from typing import Optional

# Context variables to carry tracing identifiers across async boundaries
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


def set_current_trace_id(trace_id: Optional[str]) -> None:
    _trace_id_var.set(trace_id)


def get_current_trace_id() -> Optional[str]:
    return _trace_id_var.get()


def set_current_request_id(request_id: Optional[str]) -> None:
    _request_id_var.set(request_id)


def get_current_request_id() -> Optional[str]:
    return _request_id_var.get()
