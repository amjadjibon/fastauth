from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.core.config import settings


def setup_telemetry() -> None:
    if not settings.otel_enabled:
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter == "otlp" and settings.otel_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    elif settings.otel_exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)


def instrument_app(app) -> None:
    if not settings.otel_enabled:
        return

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine) -> None:
    if not settings.otel_enabled:
        return

    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    # AsyncEngine wraps a sync engine; the instrumentation hooks into sync events.
    sync_engine = getattr(engine, "sync_engine", engine)
    SQLAlchemyInstrumentor().instrument(engine=sync_engine)


def instrument_redis(_client=None) -> None:
    if not settings.otel_enabled:
        return

    from opentelemetry.instrumentation.redis import RedisInstrumentor
    RedisInstrumentor().instrument()
