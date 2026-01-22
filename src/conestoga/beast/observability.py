from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server

class ObservabilityStack:
    def __init__(self, service_name: str, jaeger_host: str, jaeger_port: int, metrics_port: int):
        self.service_name = service_name
        self._setup_tracer(jaeger_host, jaeger_port)
        self._setup_metrics(metrics_port)

    def _setup_tracer(self, host: str, port: int):
        trace.set_tracer_provider(TracerProvider())
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"http://{host}:{port}",
        )
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
        self.tracer = trace.get_tracer(self.service_name)

    def _setup_metrics(self, port: int):
        start_http_server(port)
        self.messages_total = Counter('beast_messages_total', 'Total messages', ['type', 'direction'])
        self.processing_duration = Histogram('beast_processing_duration_seconds', 'Message processing duration')
        self.connection_status = Gauge('beast_connection_status', 'Beast connection status')
        self.hacp_violations = Counter('hacp_violations_total', 'Total HACP violations')

    def get_tracer(self):
        return self.tracer

    def inject_trace_context(self, message: dict) -> dict:
        # This is a simplified injection. In a real scenario, we'd use W3C trace context format.
        with self.tracer.start_as_current_span("send_message") as span:
            ctx = span.get_span_context()
            message.setdefault("header", {})["trace_context"] = {
                "trace_id": format(ctx.trace_id, 'x'),
                "span_id": format(ctx.span_id, 'x'),
            }
        return message

    def extract_trace_context(self, message: dict):
        # Simplified extraction.
        ctx = message.get("header", {}).get("trace_context")
        if ctx:
            return trace.SpanContext(
                trace_id=int(ctx['trace_id'], 16),
                span_id=int(ctx['span_id'], 16),
                is_remote=True,
                trace_flags=trace.TraceFlags(0x01)
            )
        return None
