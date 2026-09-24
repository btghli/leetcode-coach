"""Transient presentation events, never conversation/checkpoint state."""
from contextvars import ContextVar

event_sink = ContextVar('coach_event_sink', default=None)


def emit(kind, **data):
    sink = event_sink.get()
    if sink:
        sink({'type': kind, **data})
