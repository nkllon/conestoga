"""Tests for Beast adapter message handling and integration"""
import pytest
import json
import asyncio
from unittest.mock import Mock, MagicMock, patch
from conestoga.beast.adapter import BeastAdapter
from conestoga.beast.envelope import create_envelope, EnvelopeValidationError


class TestBeastAdapterInit:
    """Test Beast adapter initialization"""

    def test_init_basic(self):
        """Test basic adapter initialization"""
        adapter = BeastAdapter(agent_id="test-agent")

        assert adapter.agent_id == "test-agent"
        assert adapter.redis_host == "localhost"
        assert adapter.redis_port == 6379
        assert not adapter.is_connected
        assert adapter.handlers == {}
        assert adapter.pending_replies == {}

    def test_init_with_custom_redis(self):
        """Test initialization with custom Redis config"""
        adapter = BeastAdapter(
            agent_id="test-agent", redis_host="custom-host", redis_port=6380
        )

        assert adapter.redis_host == "custom-host"
        assert adapter.redis_port == 6380

    def test_init_with_observability(self):
        """Test initialization with observability stack"""
        mock_observability = Mock()
        adapter = BeastAdapter(
            agent_id="test-agent", observability_stack=mock_observability
        )

        assert adapter.observability == mock_observability

    def test_init_with_hacp(self):
        """Test initialization with HACP interceptor"""
        mock_hacp = Mock()
        adapter = BeastAdapter(agent_id="test-agent", hacp_interceptor=mock_hacp)

        assert adapter.hacp_interceptor == mock_hacp


class TestBeastAdapterHandlers:
    """Test message handler registration and dispatch"""

    def test_register_handler(self):
        """Test registering a message handler"""
        adapter = BeastAdapter(agent_id="test-agent")
        handler = Mock()

        adapter.register_handler("test_message", handler)

        assert "test_message" in adapter.handlers
        assert adapter.handlers["test_message"] == handler

    def test_dispatch_message_with_handler(self):
        """Test message dispatch to registered handler"""
        adapter = BeastAdapter(agent_id="test-agent")
        handler = Mock()
        adapter.register_handler("test_message", handler)

        message = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message", "data": "test"},
        }

        adapter._dispatch_message(message)

        handler.assert_called_once_with(message)

    def test_dispatch_message_without_handler(self):
        """Test message dispatch without registered handler logs warning"""
        adapter = BeastAdapter(agent_id="test-agent")

        message = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "unknown_message"},
        }

        # Should not raise, just log warning
        with patch("conestoga.beast.adapter.logging") as mock_logging:
            adapter._dispatch_message(message)
            mock_logging.warning.assert_called()

    def test_dispatch_with_observability(self):
        """Test message dispatch with observability tracking"""
        mock_observability = Mock()
        mock_observability.processing_duration.time.return_value.__enter__ = Mock()
        mock_observability.processing_duration.time.return_value.__exit__ = Mock()

        adapter = BeastAdapter(
            agent_id="test-agent", observability_stack=mock_observability
        )
        handler = Mock()
        adapter.register_handler("test_message", handler)

        message = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message"},
        }

        adapter._dispatch_message(message)

        # Verify observability was used
        mock_observability.processing_duration.time.assert_called_once()
        handler.assert_called_once()


class TestBeastAdapterMessageHandling:
    """Test message handling and validation"""

    def test_handle_message_valid(self):
        """Test handling a valid message"""
        adapter = BeastAdapter(agent_id="test-agent")
        handler = Mock()
        adapter.register_handler("test_message", handler)

        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={"data": "test"}
        )
        raw_message = json.dumps(envelope.to_dict())

        adapter._handle_message(raw_message)

        # Handler should be called
        assert handler.call_count == 1

    def test_handle_message_invalid_json(self):
        """Test handling invalid JSON logs error"""
        adapter = BeastAdapter(agent_id="test-agent")

        with patch("conestoga.beast.adapter.logging") as mock_logging:
            adapter._handle_message("not valid json")
            mock_logging.error.assert_called()

    def test_handle_message_invalid_envelope(self):
        """Test handling message with invalid envelope"""
        adapter = BeastAdapter(agent_id="test-agent")

        invalid_message = json.dumps({"invalid": "envelope"})

        with patch("conestoga.beast.adapter.logging") as mock_logging:
            adapter._handle_message(invalid_message)
            # Should log envelope validation error
            assert any(
                "Envelope validation failed" in str(call)
                for call in mock_logging.error.call_args_list
            )

    def test_handle_message_with_observability_metrics(self):
        """Test that message handling updates observability metrics"""
        mock_observability = Mock()
        mock_observability.messages_total.labels.return_value.inc = Mock()
        mock_observability.extract_trace_context.return_value = None
        mock_observability.get_tracer.return_value.start_as_current_span = (
            MagicMock()
        )

        adapter = BeastAdapter(
            agent_id="test-agent", observability_stack=mock_observability
        )
        handler = Mock()
        adapter.register_handler("test_message", handler)

        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={}
        )
        raw_message = json.dumps(envelope.to_dict())

        adapter._handle_message(raw_message)

        # Verify metrics were incremented
        mock_observability.messages_total.labels.assert_called()

    def test_handle_message_hacp_violation(self):
        """Test message handling blocks on HACP violation"""
        from conestoga.hacp.interceptor import HACPViolationError

        mock_hacp = Mock()
        mock_hacp.intercept.side_effect = HACPViolationError("Policy violation")

        adapter = BeastAdapter(agent_id="test-agent", hacp_interceptor=mock_hacp)
        handler = Mock()
        adapter.register_handler("test_message", handler)

        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={}
        )
        raw_message = json.dumps(envelope.to_dict())

        adapter._handle_message(raw_message)

        # Handler should NOT be called due to HACP violation
        handler.assert_not_called()

    def test_handle_message_hacp_violation_metrics(self):
        """Test HACP violation increments metrics"""
        from conestoga.hacp.interceptor import HACPViolationError

        mock_observability = Mock()
        mock_hacp = Mock()
        mock_hacp.intercept.side_effect = HACPViolationError("Policy violation")

        adapter = BeastAdapter(
            agent_id="test-agent",
            hacp_interceptor=mock_hacp,
            observability_stack=mock_observability,
        )

        envelope = create_envelope(
            sender="agent-1", message_type="test_message", payload_data={}
        )
        raw_message = json.dumps(envelope.to_dict())

        adapter._handle_message(raw_message)

        # Verify HACP violation metric was incremented
        mock_observability.hacp_violations.inc.assert_called_once()


class TestBeastAdapterSendMessage:
    """Test message sending functionality"""

    @patch("conestoga.beast.adapter.redis.Redis")
    def test_send_message_basic(self, mock_redis_class):
        """Test sending a basic message"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        adapter = BeastAdapter(agent_id="test-agent")
        adapter.connect()

        message = {
            "header": {
                "sender": "test-agent",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message"},
        }

        adapter.send_message(message)

        # Verify Redis publish was called (heartbeat + message)
        assert mock_redis.publish.call_count >= 1
        # Find the message publish call (not heartbeat)
        message_calls = [
            call for call in mock_redis.publish.call_args_list
            if call[0][0] == "beast:global:messages"
        ]
        assert len(message_calls) == 1
        args = message_calls[0][0]
        assert args[0] == "beast:global:messages"
        assert json.loads(args[1]) == message

    @patch("conestoga.beast.adapter.redis.Redis")
    def test_send_message_with_observability(self, mock_redis_class):
        """Test sending message with observability tracking"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        mock_observability = Mock()
        mock_observability.inject_trace_context.return_value = {
            "header": {"trace_context": {"trace_id": "123"}},
            "payload": {"type": "test"},
        }
        mock_observability.messages_total.labels.return_value.inc = Mock()

        adapter = BeastAdapter(
            agent_id="test-agent", observability_stack=mock_observability
        )
        adapter.connect()

        message = {"header": {}, "payload": {"type": "test_message"}}
        adapter.send_message(message)

        # Verify observability methods were called
        mock_observability.inject_trace_context.assert_called_once()
        mock_observability.messages_total.labels.assert_called()

    @patch("conestoga.beast.adapter.redis.Redis")
    def test_send_message_hacp_violation(self, mock_redis_class):
        """Test that HACP violation blocks message sending"""
        from conestoga.hacp.interceptor import HACPViolationError

        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        mock_hacp = Mock()
        mock_hacp.intercept.side_effect = HACPViolationError("Policy violation")

        adapter = BeastAdapter(agent_id="test-agent", hacp_interceptor=mock_hacp)
        adapter.connect()

        message = {"header": {}, "payload": {"type": "test_message"}}
        adapter.send_message(message)

        # Only heartbeat should be published, not the message
        message_calls = [
            call for call in mock_redis.publish.call_args_list
            if call[0][0] != "beast:global:heartbeat"
        ]
        assert len(message_calls) == 0


@pytest.mark.asyncio
class TestBeastAdapterAsync:
    """Test async adapter functionality"""

    async def test_async_register_handler(self):
        """Test async handler registration"""
        adapter = BeastAdapter(agent_id="test-agent")
        handler = Mock()

        await adapter.async_register_handler("test_message", handler)

        assert "test_message" in adapter.handlers
        assert adapter.handlers["test_message"] == handler

    async def test_async_dispatch_sync_handler(self):
        """Test async dispatch of synchronous handler"""
        adapter = BeastAdapter(agent_id="test-agent")
        handler = Mock()
        adapter.handlers["test_message"] = handler

        message = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message", "data": "test"},
        }

        await adapter._async_dispatch_message(message)

        # Handler should be called with payload
        handler.assert_called_once_with({"type": "test_message", "data": "test"})

    async def test_async_dispatch_async_handler(self):
        """Test async dispatch of async handler"""

        async def async_handler(payload):
            return payload

        adapter = BeastAdapter(agent_id="test-agent")
        adapter.handlers["test_message"] = async_handler

        message = {
            "header": {
                "sender": "agent-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "id": "msg-123",
            },
            "payload": {"type": "test_message", "data": "test"},
        }

        # Should not raise
        await adapter._async_dispatch_message(message)

    @patch("conestoga.beast.adapter.redis.Redis")
    async def test_async_send_message(self, mock_redis_class):
        """Test async message sending"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        adapter = BeastAdapter(agent_id="test-agent")
        adapter.connect()

        correlation_id = await adapter.async_send_message(
            target_agent="agent-2", message_type="test", payload={"data": "value"}
        )

        assert correlation_id is not None
        # Find the message publish call (not heartbeat)
        message_calls = [
            call for call in mock_redis.publish.call_args_list
            if call[0][0] != "beast:global:heartbeat"
        ]
        assert len(message_calls) == 1

    @patch("conestoga.beast.adapter.redis.Redis")
    async def test_async_wait_for_reply_timeout(self, mock_redis_class):
        """Test async wait for reply with timeout"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        adapter = BeastAdapter(agent_id="test-agent")
        adapter.connect()

        with pytest.raises(asyncio.TimeoutError):
            await adapter.async_wait_for_reply("nonexistent-correlation-id", timeout=0.1)

    @patch("conestoga.beast.adapter.redis.Redis")
    async def test_async_wait_for_reply_success(self, mock_redis_class):
        """Test async wait for reply receives response"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        adapter = BeastAdapter(agent_id="test-agent")
        adapter.connect()

        correlation_id = "test-correlation-123"

        # Simulate receiving a reply
        async def send_reply():
            await asyncio.sleep(0.1)
            message = {
                "header": {
                    "sender": "agent-2",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "id": "reply-123",
                },
                "payload": {
                    "type": "reply",
                    "correlation_id": correlation_id,
                    "result": "success",
                },
            }
            raw_message = json.dumps(message)
            await adapter._async_handle_message(raw_message)

        # Start both tasks
        reply_task = asyncio.create_task(send_reply())
        result = await adapter.async_wait_for_reply(correlation_id, timeout=1.0)

        await reply_task

        assert result["correlation_id"] == correlation_id
        assert result["result"] == "success"

    @patch("conestoga.beast.adapter.redis.Redis")
    async def test_async_handle_message_invalid_envelope(self, mock_redis_class):
        """Test async handling of invalid envelope"""
        adapter = BeastAdapter(agent_id="test-agent")

        invalid_message = json.dumps({"invalid": "envelope"})

        with patch("conestoga.beast.adapter.logging") as mock_logging:
            await adapter._async_handle_message(invalid_message)
            # Should log error about envelope validation
            assert any(
                "Envelope validation failed" in str(call)
                for call in mock_logging.error.call_args_list
            )

    @patch("conestoga.beast.adapter.redis.Redis")
    async def test_async_stop(self, mock_redis_class):
        """Test async adapter stop"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True
        mock_redis.close.return_value = None

        adapter = BeastAdapter(agent_id="test-agent")
        await adapter.async_start()

        # Give the subscribe task a moment to start
        await asyncio.sleep(0.1)

        # Stop the adapter
        await adapter.async_stop()

        assert not adapter.is_connected
        assert adapter._subscribe_task.cancelled() or adapter._subscribe_task.done()
