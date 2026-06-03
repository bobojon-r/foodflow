import logging
import os

logger = logging.getLogger(__name__)


def setup_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("ENVIRONMENT", "development"),
    )
    logger.info("Sentry initialized")


def setup_tracing(app: object, service_name: str) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
    logger.info("OpenTelemetry tracing initialised, endpoint=%s", endpoint)


def setup_metrics(app: object) -> None:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app)  # type: ignore[arg-type]
    logger.info("Prometheus metrics exposed at /metrics")


def setup_observability(app: object, service_name: str) -> None:
    setup_sentry()
    setup_tracing(app, service_name)
    setup_metrics(app)
