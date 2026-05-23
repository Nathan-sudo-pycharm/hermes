import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)


def setup_telemetry():
    resource = Resource.create({"service.name": "hermes-worker"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint="otel-collector:4317",
        insecure=True
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    logger.info("Tracing initialised → otel-collector:4317")


def get_tracer():
    return trace.get_tracer("hermes-worker")