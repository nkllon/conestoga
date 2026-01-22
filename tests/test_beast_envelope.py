"""Tests for Beast envelope validation and creation"""
import pytest
from datetime import datetime
from conestoga.beast.envelope import (
    BeastEnvelope,
    validate_envelope,
    create_envelope,
    EnvelopeValidationError,
)


class TestEnvelopeValidation:
    """Test envelope validation functionality"""

    def test_valid_envelope(self):
        """Test that a valid envelope passes validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message", "data": "test"},
        }
        # Should not raise an exception
        validate_envelope(envelope)

    def test_envelope_with_trace_context(self):
        """Test envelope with trace context passes validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
                "trace_context": {"trace_id": "abc123", "span_id": "def456"},
            },
            "payload": {"type": "test_message"},
        }
        validate_envelope(envelope)

    def test_envelope_with_metadata(self):
        """Test envelope with metadata passes validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message"},
            "metadata": {"role": "coordinator", "topic": "tasks"},
        }
        validate_envelope(envelope)

    def test_invalid_envelope_not_dict(self):
        """Test that non-dict envelope fails validation"""
        with pytest.raises(EnvelopeValidationError, match="must be a dictionary"):
            validate_envelope("not a dict")

    def test_missing_header(self):
        """Test that envelope without header fails validation"""
        envelope = {"payload": {"type": "test"}}
        with pytest.raises(EnvelopeValidationError, match="missing required 'header'"):
            validate_envelope(envelope)

    def test_header_not_dict(self):
        """Test that non-dict header fails validation"""
        envelope = {"header": "not a dict", "payload": {"type": "test"}}
        with pytest.raises(EnvelopeValidationError, match="Header must be a dictionary"):
            validate_envelope(envelope)

    def test_missing_header_fields(self):
        """Test that missing required header fields fail validation"""
        # Missing sender
        envelope = {
            "header": {"timestamp": "2024-01-01T12:00:00Z", "id": "msg-123"},
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="missing required field: sender"):
            validate_envelope(envelope)

        # Missing timestamp
        envelope = {
            "header": {"sender": "agent-1", "id": "msg-123"},
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="missing required field: timestamp"):
            validate_envelope(envelope)

        # Missing id
        envelope = {
            "header": {"sender": "agent-1", "timestamp": "2024-01-01T12:00:00Z"},
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="missing required field: id"):
            validate_envelope(envelope)

    def test_header_field_not_string(self):
        """Test that non-string header fields fail validation"""
        envelope = {
            "header": {"sender": 123, "timestamp": "2024-01-01T12:00:00Z", "id": "msg-123"},
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="must be a string"):
            validate_envelope(envelope)

    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format fails validation"""
        envelope = {
            "header": {"sender": "agent-1", "timestamp": "not-a-timestamp", "id": "msg-123"},
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="Invalid timestamp format"):
            validate_envelope(envelope)

    def test_invalid_trace_context(self):
        """Test that invalid trace context fails validation"""
        # trace_context not a dict
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
                "trace_context": "not-a-dict",
            },
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="trace_context must be a dictionary"):
            validate_envelope(envelope)

        # trace_id not a string
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
                "trace_context": {"trace_id": 123},
            },
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="trace_id must be a string"):
            validate_envelope(envelope)

        # span_id not a string
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
                "trace_context": {"span_id": 456},
            },
            "payload": {"type": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="span_id must be a string"):
            validate_envelope(envelope)

    def test_missing_payload(self):
        """Test that envelope without payload fails validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            }
        }
        with pytest.raises(EnvelopeValidationError, match="missing required 'payload'"):
            validate_envelope(envelope)

    def test_payload_not_dict(self):
        """Test that non-dict payload fails validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": "not a dict",
        }
        with pytest.raises(EnvelopeValidationError, match="Payload must be a dictionary"):
            validate_envelope(envelope)

    def test_missing_payload_type(self):
        """Test that payload without type fails validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"data": "test"},
        }
        with pytest.raises(EnvelopeValidationError, match="missing required 'type' field"):
            validate_envelope(envelope)

    def test_payload_type_not_string(self):
        """Test that non-string payload type fails validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": 123},
        }
        with pytest.raises(EnvelopeValidationError, match="Payload 'type' must be a string"):
            validate_envelope(envelope)

    def test_metadata_not_dict(self):
        """Test that non-dict metadata fails validation"""
        envelope = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test"},
            "metadata": "not a dict",
        }
        with pytest.raises(EnvelopeValidationError, match="Metadata must be a dictionary"):
            validate_envelope(envelope)


class TestEnvelopeCreation:
    """Test envelope creation functionality"""

    def test_create_envelope_basic(self):
        """Test creating a basic envelope"""
        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={"key": "value"}
        )

        assert isinstance(envelope, BeastEnvelope)
        envelope_dict = envelope.to_dict()

        assert envelope_dict["header"]["sender"] == "agent-1"
        assert envelope_dict["payload"]["type"] == "test_message"
        assert envelope_dict["payload"]["key"] == "value"
        assert "id" in envelope_dict["header"]
        assert "timestamp" in envelope_dict["header"]

        # Validate the created envelope
        validate_envelope(envelope_dict)

    def test_create_envelope_with_message_id(self):
        """Test creating envelope with custom message ID"""
        envelope = create_envelope(
            sender="agent-1",
            message_type="test_message",
            payload_data={},
            message_id="custom-id-123",
        )

        envelope_dict = envelope.to_dict()
        assert envelope_dict["header"]["id"] == "custom-id-123"

    def test_create_envelope_with_metadata(self):
        """Test creating envelope with metadata"""
        metadata = {"role": "worker", "priority": "high"}
        envelope = create_envelope(
            sender="agent-1",
            message_type="test_message",
            payload_data={},
            metadata=metadata,
        )

        envelope_dict = envelope.to_dict()
        assert envelope_dict["metadata"] == metadata

    def test_create_envelope_timestamp_format(self):
        """Test that created envelope has valid ISO timestamp"""
        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={}
        )

        envelope_dict = envelope.to_dict()
        timestamp = envelope_dict["header"]["timestamp"]

        # Should be able to parse the timestamp
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_create_envelope_validates(self):
        """Test that created envelopes are automatically validated"""
        # This should not raise an exception
        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={"data": "test"}
        )
        assert envelope is not None


class TestBeastEnvelope:
    """Test BeastEnvelope class functionality"""

    def test_envelope_to_dict(self):
        """Test converting envelope to dictionary"""
        header = {"sender": "agent-1", "timestamp": "2024-01-01T12:00:00Z", "id": "msg-123"}
        payload = {"type": "test", "data": "value"}
        metadata = {"role": "worker"}

        envelope = BeastEnvelope(header=header, payload=payload, metadata=metadata)
        result = envelope.to_dict()

        assert result["header"] == header
        assert result["payload"] == payload
        assert result["metadata"] == metadata

    def test_envelope_to_dict_no_metadata(self):
        """Test converting envelope without metadata to dictionary"""
        header = {"sender": "agent-1", "timestamp": "2024-01-01T12:00:00Z", "id": "msg-123"}
        payload = {"type": "test"}

        envelope = BeastEnvelope(header=header, payload=payload)
        result = envelope.to_dict()

        assert result["header"] == header
        assert result["payload"] == payload
        assert "metadata" not in result

    def test_envelope_from_dict(self):
        """Test creating envelope from dictionary"""
        data = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test", "data": "value"},
            "metadata": {"role": "worker"},
        }

        envelope = BeastEnvelope.from_dict(data)

        assert envelope.header == data["header"]
        assert envelope.payload == data["payload"]
        assert envelope.metadata == data["metadata"]

    def test_envelope_from_dict_validates(self):
        """Test that from_dict validates the input"""
        invalid_data = {
            "header": {"sender": "agent-1"},  # Missing required fields
            "payload": {"type": "test"},
        }

        with pytest.raises(EnvelopeValidationError):
            BeastEnvelope.from_dict(invalid_data)

    def test_envelope_roundtrip(self):
        """Test that to_dict and from_dict are inverses"""
        original = create_envelope(
            sender="agent-1",
            message_type="test",
            payload_data={"key": "value"},
            metadata={"role": "worker"},
        )

        # Convert to dict and back
        dict_form = original.to_dict()
        reconstructed = BeastEnvelope.from_dict(dict_form)

        # Should have the same content
        assert reconstructed.to_dict() == original.to_dict()
