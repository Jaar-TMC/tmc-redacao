"""
Request context propagation for cost tracking.

Uses Python ContextVar to propagate user_id, action_type, source_id, and
correlation_id from HTTP/timer handlers down to llm_service._call_api()
without changing function signatures.

Azure Functions v2 runs each request in its own async context, so ContextVar
is scoped per-task and doesn't leak between concurrent requests.
"""

from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar('current_user_id', default=None)
current_action_type: ContextVar[str | None] = ContextVar('current_action_type', default=None)
current_source_id: ContextVar[str | None] = ContextVar('current_source_id', default=None)
current_correlation_id: ContextVar[str | None] = ContextVar('current_correlation_id', default=None)
