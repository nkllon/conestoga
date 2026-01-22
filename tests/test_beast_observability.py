"""Tests for Beast observability trace context and metrics"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from prometheus_client import REGISTRY
from conestoga.beast.observability import ObservabilityStack


@pytest.fixture(autouse=True)
def cleanup_prometheus_registry():
    """Clean up Prometheus registry after each test"""
    # Remove any existing beast metrics before each test
    collectors_to_remove = []
    for collector in list(REGISTRY._collector_to_names.keys()):
        for name in REGISTRY._collector_to_names.get(collector, []):
            if name.startswith('beast_') or name.startswith('hacp_'):
                collectors_to_remove.append(collector)
                break
    
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    
    yield
    
    # Clean up after test
    collectors_to_remove = []
    for collector in list(REGISTRY._collector_to_names.keys()):
        for name in REGISTRY._collector_to_names.get(collector, []):
            if name.startswith('beast_') or name.startswith('hacp_'):
                collectors_to_remove.append(collector)
                break
    
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


class TestObservabilityStackInit:
    """Test observability stack initialization"""

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_init_basic(self, mock_trace, mock_exporter, mock_http_server):
        """Test basic observability stack initialization"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        assert stack.service_name == "test-service"
        mock_http_server.assert_called_once_with(9090)
        mock_exporter.assert_called_once()

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_setup_tracer(self, mock_trace, mock_exporter, mock_http_server):
        """Test tracer setup with correct endpoint"""
        mock_tracer_provider = Mock()
        mock_trace.set_tracer_provider = Mock()
        mock_trace.get_tracer_provider.return_value = mock_tracer_provider
        mock_trace.get_tracer.return_value = Mock()

        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="jaeger.example.com",
            jaeger_port=4318,
            metrics_port=9090,
        )

        # Verify exporter was created with correct endpoint
        mock_exporter.assert_called_once_with(
            endpoint="http://jaeger.example.com:4318"
        )

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_setup_metrics(self, mock_trace, mock_exporter, mock_http_server):
        """Test metrics setup"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9091,
        )

        # Verify metrics are created
        assert hasattr(stack, "messages_total")
        assert hasattr(stack, "processing_duration")
        assert hasattr(stack, "connection_status")
        assert hasattr(stack, "hacp_violations")

        # Verify HTTP server started on correct port
        mock_http_server.assert_called_once_with(9091)


class TestObservabilityStackTracer:
    """Test tracer functionality"""

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_get_tracer(self, mock_trace, mock_exporter, mock_http_server):
        """Test getting tracer instance"""
        mock_tracer = Mock()
        mock_trace.get_tracer.return_value = mock_tracer

        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        tracer = stack.get_tracer()
        assert tracer == mock_tracer


class TestObservabilityStackTraceContext:
    """Test trace context injection and extraction"""

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_inject_trace_context(self, mock_trace, mock_exporter, mock_http_server):
        """Test trace context injection into message"""
        # Setup mock span context
        mock_span_context = Mock()
        mock_span_context.trace_id = 0x1234567890ABCDEF
        mock_span_context.span_id = 0xFEDCBA0987654321

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)

        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        message = {"header": {}, "payload": {"type": "test"}}
        result = stack.inject_trace_context(message)

        # Verify trace context was added
        assert "trace_context" in result["header"]
        assert "trace_id" in result["header"]["trace_context"]
        assert "span_id" in result["header"]["trace_context"]

        # Verify IDs are hex strings
        assert isinstance(result["header"]["trace_context"]["trace_id"], str)
        assert isinstance(result["header"]["trace_context"]["span_id"], str)

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_inject_trace_context_creates_header(
        self, mock_trace, mock_exporter, mock_http_server
    ):
        """Test trace context injection creates header if missing"""
        mock_span_context = Mock()
        mock_span_context.trace_id = 0xABCDEF
        mock_span_context.span_id = 0x123456

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)

        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Message without header
        message = {"payload": {"type": "test"}}
        result = stack.inject_trace_context(message)

        # Header should be created
        assert "header" in result
        assert "trace_context" in result["header"]

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_extract_trace_context_valid(
        self, mock_trace, mock_exporter, mock_http_server
    ):
        """Test trace context extraction from message"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        message = {
            "header": {
                "trace_context": {"trace_id": "1234567890abcdef", "span_id": "fedcba0987654321"}
            }
        }

        with patch("conestoga.beast.observability.trace.SpanContext") as mock_span_context:
            result = stack.extract_trace_context(message)

            # Verify SpanContext was created with correct parameters
            mock_span_context.assert_called_once()
            call_args = mock_span_context.call_args[1]
            assert call_args["trace_id"] == int("1234567890abcdef", 16)
            assert call_args["span_id"] == int("fedcba0987654321", 16)
            assert call_args["is_remote"] is True

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_extract_trace_context_missing(
        self, mock_trace, mock_exporter, mock_http_server
    ):
        """Test trace context extraction returns None when missing"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Message without trace context
        message = {"header": {}}
        result = stack.extract_trace_context(message)

        assert result is None

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_extract_trace_context_no_header(
        self, mock_trace, mock_exporter, mock_http_server
    ):
        """Test trace context extraction with no header"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Message without header
        message = {"payload": {"type": "test"}}
        result = stack.extract_trace_context(message)

        assert result is None

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    def test_trace_context_roundtrip(self, mock_trace, mock_exporter, mock_http_server):
        """Test that inject and extract are compatible"""
        # Setup mock for injection
        mock_span_context = Mock()
        mock_span_context.trace_id = 0x1234567890ABCDEF
        mock_span_context.span_id = 0xFEDCBA0987654321

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)

        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer

        # Mock SpanContext for extraction
        extracted_context = Mock()
        with patch(
            "conestoga.beast.observability.trace.SpanContext",
            return_value=extracted_context,
        ):
            stack = ObservabilityStack(
                service_name="test-service",
                jaeger_host="localhost",
                jaeger_port=4317,
                metrics_port=9090,
            )

            # Inject trace context
            message = {"header": {}, "payload": {"type": "test"}}
            injected_message = stack.inject_trace_context(message)

            # Extract trace context
            result = stack.extract_trace_context(injected_message)

            # Should have extracted a context
            assert result == extracted_context


class TestObservabilityStackMetrics:
    """Test metrics functionality"""

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    @patch("conestoga.beast.observability.Counter")
    def test_messages_total_counter(
        self, mock_counter, mock_trace, mock_exporter, mock_http_server
    ):
        """Test messages_total counter creation"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Verify Counter was called for messages_total
        assert any(
            call[0][0] == "beast_messages_total" for call in mock_counter.call_args_list
        )

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    @patch("conestoga.beast.observability.Histogram")
    def test_processing_duration_histogram(
        self, mock_histogram, mock_trace, mock_exporter, mock_http_server
    ):
        """Test processing_duration histogram creation"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Verify Histogram was called for processing_duration
        assert any(
            call[0][0] == "beast_processing_duration_seconds"
            for call in mock_histogram.call_args_list
        )

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    @patch("conestoga.beast.observability.Gauge")
    def test_connection_status_gauge(
        self, mock_gauge, mock_trace, mock_exporter, mock_http_server
    ):
        """Test connection_status gauge creation"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Verify Gauge was called for connection_status
        assert any(
            call[0][0] == "beast_connection_status" for call in mock_gauge.call_args_list
        )

    @patch("conestoga.beast.observability.start_http_server")
    @patch("conestoga.beast.observability.OTLPSpanExporter")
    @patch("conestoga.beast.observability.trace")
    @patch("conestoga.beast.observability.Counter")
    def test_hacp_violations_counter(
        self, mock_counter, mock_trace, mock_exporter, mock_http_server
    ):
        """Test hacp_violations counter creation"""
        stack = ObservabilityStack(
            service_name="test-service",
            jaeger_host="localhost",
            jaeger_port=4317,
            metrics_port=9090,
        )

        # Verify Counter was called for hacp_violations
        assert any(
            call[0][0] == "hacp_violations_total" for call in mock_counter.call_args_list
        )
