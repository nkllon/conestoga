"""
Beast Envelope Validation Module

Provides validation for Beast message envelopes to ensure conformance
with the standard Beast message format.
"""

import logging
from datetime import UTC, datetime
from typing import Any


class EnvelopeValidationError(Exception):
    """Raised when envelope validation fails."""

    pass


class BeastEnvelope:
    """
    Represents a Beast message envelope with header and payload.

    Standard Beast envelope format:
    {
        "header": {
            "sender": "agent-id",
            "timestamp": "ISO-8601 timestamp",
            "id": "unique-message-id",
            "trace_context": {  # Optional
                "trace_id": "hex-trace-id",
                "span_id": "hex-span-id"
            }
        },
        "payload": {
            "type": "message-type",
            ... # Type-specific payload data
        },
        "metadata": {  # Optional
            "role": "role-name",
            "topic": "topic-name"
        }
    }
    """

    def __init__(
        self,
        header: dict[str, Any],
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ):
        self.header = header
        self.payload = payload
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert envelope to dictionary format."""
        result = {"header": self.header, "payload": self.payload}
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BeastEnvelope":
        """Create envelope from dictionary, with validation."""
        validate_envelope(data)
        return cls(
            header=data["header"],
            payload=data["payload"],
            metadata=data.get("metadata"),
        )


def validate_envelope(envelope: dict[str, Any]) -> None:
    """
    Validates a Beast message envelope.

    Args:
        envelope: The envelope dictionary to validate

    Raises:
        EnvelopeValidationError: If validation fails
    """
    # Validate top-level structure
    if not isinstance(envelope, dict):
        raise EnvelopeValidationError("Envelope must be a dictionary")

    # Validate header presence and structure
    if "header" not in envelope:
        raise EnvelopeValidationError("Envelope missing required 'header' field")

    header = envelope["header"]
    if not isinstance(header, dict):
        raise EnvelopeValidationError("Header must be a dictionary")

    # Validate required header fields
    required_header_fields = ["sender", "timestamp", "id"]
    for field in required_header_fields:
        if field not in header:
            raise EnvelopeValidationError(f"Header missing required field: {field}")
        if not isinstance(header[field], str):
            raise EnvelopeValidationError(f"Header field '{field}' must be a string")

    # Validate timestamp format
    try:
        datetime.fromisoformat(header["timestamp"].replace("Z", "+00:00"))
    except (ValueError, AttributeError) as err:
        raise EnvelopeValidationError(
            f"Invalid timestamp format: {header.get('timestamp')}"
        ) from err

    # Validate trace_context if present
    if "trace_context" in header:
        trace_ctx = header["trace_context"]
        if not isinstance(trace_ctx, dict):
            raise EnvelopeValidationError("trace_context must be a dictionary")
        if "trace_id" in trace_ctx and not isinstance(trace_ctx["trace_id"], str):
            raise EnvelopeValidationError("trace_id must be a string")
        if "span_id" in trace_ctx and not isinstance(trace_ctx["span_id"], str):
            raise EnvelopeValidationError("span_id must be a string")

    # Validate payload presence and structure
    if "payload" not in envelope:
        raise EnvelopeValidationError("Envelope missing required 'payload' field")

    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise EnvelopeValidationError("Payload must be a dictionary")

    # Validate payload type field
    if "type" not in payload:
        raise EnvelopeValidationError("Payload missing required 'type' field")
    if not isinstance(payload["type"], str):
        raise EnvelopeValidationError("Payload 'type' must be a string")

    # Validate metadata if present
    if "metadata" in envelope:
        metadata = envelope["metadata"]
        if not isinstance(metadata, dict):
            raise EnvelopeValidationError("Metadata must be a dictionary")

    logging.debug(f"Envelope validation passed for message ID: {header['id']}")


def create_envelope(
    sender: str,
    message_type: str,
    payload_data: dict[str, Any],
    message_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BeastEnvelope:
    """
    Creates a valid Beast envelope.

    Args:
        sender: Agent ID of the sender
        message_type: Type of the message
        payload_data: Additional payload data beyond type
        message_id: Optional message ID (generated if not provided)
        metadata: Optional metadata dictionary

    Returns:
        BeastEnvelope: A validated envelope
    """
    import uuid

    if message_id is None:
        message_id = str(uuid.uuid4())

    header = {
        "sender": sender,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "id": message_id,
    }

    payload = {"type": message_type, **payload_data}

    envelope = BeastEnvelope(header=header, payload=payload, metadata=metadata)

    # Validate before returning
    validate_envelope(envelope.to_dict())

    return envelope
