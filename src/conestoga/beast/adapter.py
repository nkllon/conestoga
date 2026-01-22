import redis
import time
import logging
import threading
import json
import asyncio
import uuid
from typing import Optional, Callable, Dict, Any

from conestoga.hacp.interceptor import HACPInterceptor, HACPViolationError


class BeastAdapter:
    def __init__(
        self,
        agent_id: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        observability_stack=None,
        hacp_interceptor=None,
    ):
        self.agent_id = agent_id
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client = None
        self.is_connected = False
        self.observability = observability_stack
        self.hacp_interceptor = hacp_interceptor
        self.handlers = {}  # Initialize handlers dictionary
        self.pending_replies: Dict[str, asyncio.Future] = {}  # For async reply handling
        self._subscribe_task: Optional[asyncio.Task] = None

    def connect(self):
        """
        Connects to the Redis server and authenticates the agent.
        """
        retry_delay = 1
        while not self.is_connected:
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                self.redis_client.ping()
                self.is_connected = True
                logging.info("BeastAdapter connected to Redis.")
                self._start_heartbeat()
            except (
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError,
            ) as e:
                logging.error(
                    f"Redis connection failed: {e}. Retrying in {retry_delay} seconds."
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)

    def _start_heartbeat(self):
        """
        Starts sending a periodic heartbeat to the Beast network.
        """

        def heartbeat_task():
            while self.is_connected:
                try:
                    self.redis_client.publish("beast:global:heartbeat", self.agent_id)
                    if self.observability:
                        self.observability.connection_status.set(
                            1
                        )  # Set connection status to 1 (connected)
                    time.sleep(10)
                except redis.exceptions.ConnectionError:
                    if self.observability:
                        self.observability.connection_status.set(
                            0
                        )  # Set connection status to 0 (disconnected)
                    self.is_connected = False
                    logging.error("Heartbeat failed. Reconnecting...")
                    self.connect()  # Attempt to reconnect

        heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True)
        heartbeat_thread.start()

    def register_handler(self, message_type: str, handler):
        self.handlers[message_type] = handler

    def _subscribe(self):
        """
        Subscribes to the agent's inbox and broadcast channels.
        """
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(f"beast:agent:{self.agent_id}:inbox")
        pubsub.subscribe("beast:global:announcements")

        for message in pubsub.listen():
            if message["type"] == "message":
                self._handle_message(message["data"])

    def _handle_message(self, raw_message: str):
        """
        Deserializes and routes an incoming message.
        """
        from conestoga.beast.envelope import validate_envelope, EnvelopeValidationError

        try:
            message = json.loads(raw_message)

            # Validate envelope format
            try:
                validate_envelope(message)
            except EnvelopeValidationError as e:
                logging.error(f"Envelope validation failed: {e}")
                if self.observability:
                    self.observability.messages_total.labels(
                        type="invalid", direction="in"
                    ).inc()
                return  # Reject malformed message

            if self.hacp_interceptor:
                try:
                    message = self.hacp_interceptor.intercept(message, "in")
                except HACPViolationError:
                    if self.observability:
                        self.observability.hacp_violations.inc()
                    return  # Block message due to HACP violation

            if self.observability:
                self.observability.messages_total.labels(
                    type=message.get("payload", {}).get("type", "unknown"),
                    direction="in",
                ).inc()
                parent_context = self.observability.extract_trace_context(message)
                with self.observability.get_tracer().start_as_current_span(
                    "handle_message", context=parent_context
                ):
                    self._dispatch_message(message)
            else:
                self._dispatch_message(message)

        except json.JSONDecodeError:
            logging.error("Failed to decode incoming message.")
        except Exception as e:
            logging.error(f"Error handling message: {e}")

    def _dispatch_message(self, message):
        message_type = message.get("payload", {}).get("type")
        if message_type in self.handlers:
            if self.observability:
                with self.observability.processing_duration.time():
                    self.handlers[message_type](message)
            else:
                self.handlers[message_type](message)
        else:
            logging.warning(f"No handler for message type: {message_type}")

    def send_message(self, message: dict):
        """
        Serializes and sends a message to the Beast network.
        """
        if self.hacp_interceptor:
            try:
                message = self.hacp_interceptor.intercept(message, "out")
            except HACPViolationError:
                if self.observability:
                    self.observability.hacp_violations.inc()
                return  # Block message due to HACP violation

        if self.observability:
            message = self.observability.inject_trace_context(message)
            self.observability.messages_total.labels(
                type=message.get("payload", {}).get("type", "unknown"), direction="out"
            ).inc()

        try:
            channel = "beast:global:messages"  # Default channel, could be dynamic based on message content
            self.redis_client.publish(channel, json.dumps(message))
        except redis.exceptions.ConnectionError:
            logging.error("Failed to send message due to connection error.")
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    def start(self):
        """
        Connects and starts listening for messages.
        """
        self.connect()
        # The subscription loop should ideally run in a separate thread to not block the main process
        subscribe_thread = threading.Thread(target=self._subscribe, daemon=True)
        subscribe_thread.start()

    # Async methods for async/await support
    async def async_start(self):
        """
        Async version of start() for use in async contexts.
        """
        await asyncio.to_thread(self.connect)
        self._subscribe_task = asyncio.create_task(self._async_subscribe())

    async def async_stop(self):
        """
        Stops the adapter and closes connections.
        """
        self.is_connected = False
        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                # Task cancellation is expected when stopping the adapter.
                logging.debug("Subscribe task cancelled during async_stop (expected during shutdown).")
        if self.redis_client:
            await asyncio.to_thread(self.redis_client.close)

    async def _async_subscribe(self):
        """
        Async version of subscribe loop.
        """
        pubsub = await asyncio.to_thread(self.redis_client.pubsub)
        await asyncio.to_thread(pubsub.subscribe, f"beast:agent:{self.agent_id}:inbox")
        await asyncio.to_thread(pubsub.subscribe, "beast:global:announcements")

        while self.is_connected:
            try:
                message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
                if message and message["type"] == "message":
                    await self._async_handle_message(message["data"])
            except Exception as e:
                if self.is_connected:
                    logging.error(f"Error in async subscribe loop: {e}")
                break

    async def _async_handle_message(self, raw_message: str):
        """
        Async version of message handler.
        """
        from conestoga.beast.envelope import validate_envelope, EnvelopeValidationError

        try:
            message = json.loads(raw_message)

            # Validate envelope format
            try:
                validate_envelope(message)
            except EnvelopeValidationError as e:
                logging.error(f"Envelope validation failed: {e}")
                if self.observability:
                    self.observability.messages_total.labels(
                        type="invalid", direction="in"
                    ).inc()
                return

            if self.hacp_interceptor:
                try:
                    message = self.hacp_interceptor.intercept(message, "in")
                except HACPViolationError:
                    if self.observability:
                        self.observability.hacp_violations.inc()
                    return

            # Check if this is a reply to a pending request
            correlation_id = message.get("payload", {}).get("correlation_id")
            if correlation_id and correlation_id in self.pending_replies:
                future = self.pending_replies.pop(correlation_id)
                future.set_result(message.get("payload"))
                return

            if self.observability:
                self.observability.messages_total.labels(
                    type=message.get("payload", {}).get("type", "unknown"),
                    direction="in",
                ).inc()

            await self._async_dispatch_message(message)

        except json.JSONDecodeError:
            logging.error("Failed to decode incoming message.")
        except Exception as e:
            logging.error(f"Error handling message: {e}")

    async def _async_dispatch_message(self, message):
        """
        Async version of message dispatcher.
        """
        message_type = message.get("payload", {}).get("type")
        if message_type in self.handlers:
            handler = self.handlers[message_type]
            if asyncio.iscoroutinefunction(handler):
                await handler(message.get("payload"))
            else:
                await asyncio.to_thread(handler, message.get("payload"))
        else:
            logging.warning(f"No handler for message type: {message_type}")

    async def async_send_message(
        self, target_agent: str, message_type: str, payload: dict
    ) -> str:
        """
        Async version of send_message that returns a correlation ID.
        """
        from conestoga.beast.envelope import create_envelope
        from datetime import datetime

        correlation_id = str(uuid.uuid4())
        payload["correlation_id"] = correlation_id

        # Create proper Beast envelope
        envelope = create_envelope(
            sender=self.agent_id,
            message_type=message_type,
            payload_data=payload,
            message_id=str(uuid.uuid4()),
            metadata={"recipient": target_agent},
        )

        message = envelope.to_dict()

        if self.hacp_interceptor:
            try:
                message = self.hacp_interceptor.intercept(message, "out")
            except HACPViolationError:
                if self.observability:
                    self.observability.hacp_violations.inc()
                raise

        if self.observability:
            message = self.observability.inject_trace_context(message)
            self.observability.messages_total.labels(
                type=message_type, direction="out"
            ).inc()

        try:
            channel = f"beast:agent:{target_agent}:inbox"
            await asyncio.to_thread(
                self.redis_client.publish, channel, json.dumps(message)
            )
            return correlation_id
        except redis.exceptions.ConnectionError:
            logging.error("Failed to send message due to connection error.")
            raise
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            raise

    async def async_wait_for_reply(
        self, correlation_id: str, timeout: float = 30.0
    ) -> dict:
        """
        Waits for a reply with the given correlation ID.
        """
        future = asyncio.Future()
        self.pending_replies[correlation_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.pending_replies.pop(correlation_id, None)
            raise

    async def async_register_handler(self, message_type: str, handler: Callable):
        """
        Registers a handler for a specific message type.
        """
        self.handlers[message_type] = handler
