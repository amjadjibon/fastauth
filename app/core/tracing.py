"""Helper functions for adding auth-specific span attributes to OpenTelemetry traces."""

from opentelemetry import trace

_tracer = trace.get_tracer("fastauth")


def set_auth_span_attributes(
    user_id: str | None = None,
    auth_method: str | None = None,
    oauth_provider: str | None = None,
    mfa_success: bool | None = None,
) -> None:
    span = trace.get_current_span()
    if not span.is_recording():
        return
    if user_id:
        span.set_attribute("user.id", user_id)
    if auth_method:
        span.set_attribute("auth.method", auth_method)
    if oauth_provider:
        span.set_attribute("oauth.provider", oauth_provider)
    if mfa_success is not None:
        span.set_attribute("mfa.success", mfa_success)


def get_tracer() -> trace.Tracer:
    return _tracer
