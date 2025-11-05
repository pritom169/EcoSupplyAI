"""Shared OpenTelemetry tracing and metrics setup for all EcoSupplyAI services."""

from __future__ import annotations

import functools
import os
import time
from typing import Any, Callable, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metrics_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import MeterProvider as SDKMeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import StatusCode, Tracer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
_ENV = os.getenv("DEPLOYMENT_ENV", "production")
_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")


def _build_resource(service_name: str) -> Resource:
    return Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: _VERSION,
            ResourceAttributes.SERVICE_NAMESPACE: "ecosupplyai",
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: _ENV,
        }
    )


def setup_tracing(service_name: str) -> Tracer:
    """Configure OTLP trace exporter and return a Tracer."""
    resource = _build_resource(service_name)
    exporter = OTLPSpanExporter(
        endpoint=_OTEL_ENDPOINT,
        insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
    )
    processor = BatchSpanProcessor(exporter, max_queue_size=2048, max_export_batch_size=512)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name, _VERSION)


class ServiceMetrics:
    """Standard EcoSupplyAI service metrics."""

    def __init__(self, meter: Meter) -> None:
        self.request_counter = meter.create_counter(
            "ecosupplyai.http.requests", description="Total HTTP requests", unit="1"
        )
        self.request_duration = meter.create_histogram(
            "ecosupplyai.http.request.duration", description="Request duration", unit="s"
        )
        self.error_counter = meter.create_counter(
            "ecosupplyai.http.errors", description="HTTP error responses", unit="1"
        )
        self.llm_token_counter = meter.create_counter(
            "ecosupplyai.llm.token_usage", description="LLM tokens consumed", unit="1"
        )


def setup_metrics(service_name: str) -> tuple[Meter, ServiceMetrics]:
    """Configure OTLP metrics exporter and return a Meter + ServiceMetrics."""
    resource = _build_resource(service_name)
    exporter = OTLPMetricExporter(
        endpoint=_OTEL_ENDPOINT,
        insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
    )
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15000)
    provider = SDKMeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(service_name, _VERSION)
    return meter, ServiceMetrics(meter)


class TracingMiddleware(BaseHTTPMiddleware):
    """Auto-traces every HTTP request and records duration/error metrics."""

    def __init__(self, app: Any, tracer: Tracer, service_metrics: ServiceMetrics) -> None:
        super().__init__(app)
        self.tracer = tracer
        self.metrics = service_metrics

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method, path = request.method, request.url.path
        with self.tracer.start_as_current_span(
            f"{method} {path}",
            attributes={"http.method": method, "http.route": path, "http.url": str(request.url)},
        ) as span:
            start = time.perf_counter()
            try:
                response = await call_next(request)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                self.metrics.error_counter.add(1, {"http.method": method, "http.route": path})
                raise
            duration = time.perf_counter() - start
            span.set_attribute("http.status_code", response.status_code)
            labels = {"http.method": method, "http.route": path, "http.status_code": str(response.status_code)}
            self.metrics.request_counter.add(1, labels)
            self.metrics.request_duration.record(duration, labels)
            if response.status_code >= 400:
                self.metrics.error_counter.add(1, labels)
            return response


def instrument_fastapi(app: Any, service_name: str) -> tuple[Tracer, ServiceMetrics]:
    """One-call setup: tracing + metrics + middleware for a FastAPI app."""
    tracer = setup_tracing(service_name)
    _meter, svc_metrics = setup_metrics(service_name)
    app.add_middleware(TracingMiddleware, tracer=tracer, service_metrics=svc_metrics)
    FastAPIInstrumentor.instrument_app(app)
    return tracer, svc_metrics


def trace_method(span_name: Optional[str] = None, attributes: Optional[dict[str, str]] = None) -> Callable:
    """Decorator that wraps a sync or async function in an OpenTelemetry span."""

    def decorator(func: Callable) -> Callable:
        _name = span_name or f"{func.__module__}.{func.__qualname__}"

        import asyncio

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(_name, attributes=attributes or {}) as span:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        span.set_status(StatusCode.ERROR, str(exc))
                        span.record_exception(exc)
                        raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(_name, attributes=attributes or {}) as span:
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:
                        span.set_status(StatusCode.ERROR, str(exc))
                        span.record_exception(exc)
                        raise

            return sync_wrapper

    return decorator
