"""Tests for GeminiEventService"""
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from google import genai
from google.genai import types
from pydantic import ValidationError

from conestoga.models.events import EventDraft, EventResolution, EventType, RiskLevel
from conestoga.services.gemini_event_service import (
    GeminiEventService,
    GeminiEventServiceConfig,
    GeminiEventServiceError,
)


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing"""
    return "test-api-key-12345"


@pytest.fixture
def service_config():
    """Provide a basic service configuration"""
    return GeminiEventServiceConfig(
        model="gemini-3-flash-preview",
        thinking_level="low",
        max_output_tokens=2048,
        max_attempts=3,
        initial_backoff_s=0.1,  # Reduced for faster tests
    )


@pytest.fixture
def mock_game_state():
    """Provide a mock game state for testing"""
    return {
        "date": "1848-04-15",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "role": "leader", "health": 100},
            {"name": "Mary", "role": "cook", "health": 100},
        ],
        "resources": {
            "food": 500,
            "ammo": 100,
            "money": 200,
            "medicine": 20,
            "clothing": 50,
            "oxen": 4,
            "wagon_parts": 10,
        },
        "inventory": [
            {"item_id": "shovel", "quantity": 1},
            {"item_id": "rope", "quantity": 2},
        ],
        "flags": ["has_visited_fort"],
        "recent_log": ["Started journey", "Purchased supplies"],
    }


@pytest.fixture
def mock_event_draft():
    """Provide a mock EventDraft for testing"""
    return EventDraft(
        schema_version="event_draft.v1",
        event_id="test-event-123",
        title="River Crossing",
        event_type=EventType.HAZARD,
        scene_text="You've reached a river. The water looks deep and the current is strong.",
        choices=[
            {
                "choice_id": "A",
                "label": "Ford the river",
                "prompt": "Attempt to cross by walking through the water",
                "risk": RiskLevel.HIGH,
                "requirements": [],
            },
            {
                "choice_id": "B",
                "label": "Use the ferry",
                "prompt": "Pay for a ferry crossing",
                "risk": RiskLevel.LOW,
                "requirements": [
                    {
                        "requirement_type": "resource_at_least",
                        "ui_text": "Requires 50 money",
                        "resource": "money",
                        "min_value": 50,
                    }
                ],
            },
        ],
        safety_warnings=[],
        debug_tags=["river", "crossing"],
    )


class TestGeminiEventServiceConfig:
    """Tests for GeminiEventServiceConfig"""

    def test_config_initialization_with_defaults(self):
        """Test config initializes with default values"""
        config = GeminiEventServiceConfig()
        assert config.model == os.getenv("GEMINI_MODEL_ID", "gemini-3-flash-preview")
        assert config.thinking_level == "low"
        assert config.max_output_tokens == 2048
        assert config.max_attempts == 3
        assert config.initial_backoff_s == 0.6

    def test_config_initialization_with_custom_values(self):
        """Test config initializes with custom values"""
        config = GeminiEventServiceConfig(
            model="custom-model",
            thinking_level="high",
            max_output_tokens=4096,
            max_attempts=5,
            initial_backoff_s=1.0,
        )
        assert config.model == "custom-model"
        assert config.thinking_level == "high"
        assert config.max_output_tokens == 4096
        assert config.max_attempts == 5
        assert config.initial_backoff_s == 1.0

    def test_config_validation_empty_model(self):
        """Test config validation fails with empty model"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="")

    def test_config_validation_whitespace_model(self):
        """Test config validation fails with whitespace-only model"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="   ")

    def test_config_with_explicit_model_override(self):
        """Test config can be overridden with explicit model parameter"""
        # Note: os.getenv is evaluated at class definition time, not instantiation time
        # So we test explicit override instead
        config = GeminiEventServiceConfig(model="env-model-override")
        assert config.model == "env-model-override"


class TestGeminiEventServiceInitialization:
    """Tests for GeminiEventService initialization"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_service_initialization_with_api_key(self, mock_client_class, service_config, mock_api_key):
        """Test service initializes correctly with API key"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        mock_client_class.assert_called_once_with(api_key=mock_api_key)
        assert service.cfg == service_config
        assert service.safety_settings is not None
        assert len(service.safety_settings) == 4

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_service_initialization_without_api_key(self, mock_client_class, service_config):
        """Test service initializes correctly without API key (uses env)"""
        service = GeminiEventService(service_config)
        mock_client_class.assert_called_once_with()
        assert service.cfg == service_config

    def test_safety_settings_configuration(self, service_config, mock_api_key):
        """Test safety settings are properly configured"""
        with patch("conestoga.services.gemini_event_service.genai.Client"):
            service = GeminiEventService(service_config, api_key=mock_api_key)
            settings = service.safety_settings

            # Check we have all 4 harm categories
            assert len(settings) == 4

            # Verify categories are present
            categories = [s.category for s in settings]
            assert types.HarmCategory.HARM_CATEGORY_HATE_SPEECH in categories
            assert types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in categories
            assert types.HarmCategory.HARM_CATEGORY_HARASSMENT in categories
            assert types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in categories


class TestGenerateEventDraft:
    """Tests for generate_event_draft method"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_generate_event_draft_success(
        self, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test successful event draft generation"""
        # Setup mock response
        mock_response = Mock()
        mock_response.text = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": "test-uuid",
            "title": "A Wild Encounter",
            "event_type": "animal",
            "scene_text": "A deer appears on the trail.",
            "choices": [
                {
                    "choice_id": "A",
                    "label": "Hunt it",
                    "prompt": "Try to hunt the deer for food",
                    "risk": "medium",
                    "requirements": [],
                },
                {
                    "choice_id": "B",
                    "label": "Continue",
                    "prompt": "Let it go and continue on",
                    "risk": "low",
                    "requirements": [],
                },
            ],
            "safety_warnings": [],
            "debug_tags": ["animal", "deer"],
        })

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Execute
        service = GeminiEventService(service_config, api_key=mock_api_key)
        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            result = service.generate_event_draft(mock_game_state)

        # Verify
        assert isinstance(result, EventDraft)
        assert result.event_id == "test-uuid"
        assert result.title == "A Wild Encounter"
        assert result.event_type == EventType.ANIMAL
        assert len(result.choices) == 2
        mock_client.models.generate_content.assert_called_once()

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_generate_event_draft_includes_game_state(
        self, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test that game state is included in the prompt"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": "test-uuid",
            "title": "Test Event",
            "event_type": "social",
            "scene_text": "Test scene",
            "choices": [
                {
                    "choice_id": "A",
                    "label": "Test",
                    "prompt": "Test choice",
                    "risk": "low",
                    "requirements": [],
                }
            ],
            "safety_warnings": [],
            "debug_tags": [],
        })

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)
        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            service.generate_event_draft(mock_game_state)

        # Check that the call was made with a prompt containing game state
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "Independence, Missouri" in prompt
        assert "1848-04-15" in prompt
        assert "food" in prompt


class TestResolveEvent:
    """Tests for resolve_event method"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_resolve_event_success(
        self, mock_client_class, service_config, mock_api_key, mock_game_state, mock_event_draft
    ):
        """Test successful event resolution"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "schema_version": "event_resolution.v1",
            "event_id": "test-event-123",
            "choice_id": "A",
            "outcome_title": "Successful Crossing",
            "outcome_text": "You successfully ford the river.",
            "effects": [
                {
                    "op": "delta_resource",
                    "note": "Lost some clothing in crossing",
                    "resource": "clothing",
                    "delta": -5,
                }
            ],
        })

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service.resolve_event(mock_event_draft, "A", mock_game_state)

        assert isinstance(result, EventResolution)
        assert result.event_id == "test-event-123"
        assert result.choice_id == "A"
        assert result.outcome_title == "Successful Crossing"
        assert len(result.effects) == 1

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_resolve_event_with_rng(
        self, mock_client_class, service_config, mock_api_key, mock_game_state, mock_event_draft
    ):
        """Test event resolution with RNG inputs"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "schema_version": "event_resolution.v1",
            "event_id": "test-event-123",
            "choice_id": "A",
            "outcome_title": "Test Outcome",
            "outcome_text": "Test text",
            "effects": [],
        })

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)
        rng = {"roll": 75, "success": True}
        service.resolve_event(mock_event_draft, "A", mock_game_state, rng=rng)

        # Verify RNG was included in prompt
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "75" in prompt or "success" in prompt


class TestValidationAndRepair:
    """Tests for validation and JSON repair logic"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_validation_error_triggers_repair(
        self, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test that validation errors trigger repair logic"""
        # First response has invalid data
        invalid_response = Mock()
        invalid_response.text = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": "test-uuid",
            "title": "Test",
            "event_type": "invalid_type",  # Invalid enum value
            "scene_text": "Test",
            "choices": [],  # Invalid: needs at least 1 choice
            "safety_warnings": [],
            "debug_tags": [],
        })

        # Repair response has valid data
        valid_response = Mock()
        valid_response.text = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": "test-uuid",
            "title": "Fixed Event",
            "event_type": "social",
            "scene_text": "Fixed scene text",
            "choices": [
                {
                    "choice_id": "A",
                    "label": "Continue",
                    "prompt": "Keep going",
                    "risk": "low",
                    "requirements": [],
                }
            ],
            "safety_warnings": [],
            "debug_tags": [],
        })

        mock_client = Mock()
        mock_client.models.generate_content.side_effect = [invalid_response, valid_response]
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)
        
        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            # Should succeed after repair
            result = service.generate_event_draft(mock_game_state)

        assert isinstance(result, EventDraft)
        assert result.title == "Fixed Event"
        # Should have called generate_content twice (initial + repair)
        assert mock_client.models.generate_content.call_count == 2

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_repair_json_success(self, mock_client_class, service_config, mock_api_key):
        """Test successful JSON repair"""
        valid_response = Mock()
        valid_response.text = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": "test-id",
            "title": "Repaired Event",
            "event_type": "trade",
            "scene_text": "Repaired text",
            "choices": [
                {
                    "choice_id": "A",
                    "label": "Accept",
                    "prompt": "Accept the trade",
                    "risk": "low",
                    "requirements": [],
                }
            ],
            "safety_warnings": [],
            "debug_tags": [],
        })

        mock_client = Mock()
        mock_client.models.generate_content.return_value = valid_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service._repair_json(EventDraft, '{"invalid": "json"}', "Validation error")

        assert isinstance(result, EventDraft)
        assert result.title == "Repaired Event"

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_repair_json_empty_response_raises_error(
        self, mock_client_class, service_config, mock_api_key
    ):
        """Test that empty repair response raises error"""
        empty_response = Mock()
        empty_response.text = ""

        mock_client = Mock()
        mock_client.models.generate_content.return_value = empty_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with pytest.raises(GeminiEventServiceError, match="Repair call returned empty response"):
            service._repair_json(EventDraft, '{"bad": "json"}', "Error message")


class TestErrorHandling:
    """Tests for error handling scenarios"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_empty_response_raises_error(
        self, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test that empty response text raises error"""
        empty_response = Mock()
        empty_response.text = ""

        mock_client = Mock()
        mock_client.models.generate_content.return_value = empty_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            with pytest.raises(GeminiEventServiceError, match="Empty response text"):
                service.generate_event_draft(mock_game_state)

    @patch("conestoga.services.gemini_event_service.genai.Client")
    @patch("conestoga.services.gemini_event_service.time.sleep")
    def test_retry_with_backoff(
        self, mock_sleep, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test retry logic with exponential backoff"""
        # First two attempts fail, third succeeds
        mock_response = Mock()
        mock_response.text = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": "test-uuid",
            "title": "Success",
            "event_type": "discovery",
            "scene_text": "Found something",
            "choices": [
                {
                    "choice_id": "A",
                    "label": "Take it",
                    "prompt": "Pick it up",
                    "risk": "low",
                    "requirements": [],
                }
            ],
            "safety_warnings": [],
            "debug_tags": [],
        })

        mock_client = Mock()
        mock_client.models.generate_content.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            mock_response,
        ]
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            result = service.generate_event_draft(mock_game_state)

        assert isinstance(result, EventDraft)
        assert result.title == "Success"
        # Should have slept twice (after first and second failure)
        assert mock_sleep.call_count == 2
        # Check backoff timing
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 0.1  # initial_backoff_s
        assert sleep_calls[1] == pytest.approx(0.18, rel=0.01)  # 0.1 * 1.8

    @patch("conestoga.services.gemini_event_service.genai.Client")
    @patch("conestoga.services.gemini_event_service.time.sleep")
    def test_max_attempts_exceeded_raises_error(
        self, mock_sleep, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test that exceeding max attempts raises error"""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("Persistent API Error")
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            with pytest.raises(
                GeminiEventServiceError,
                match="Gemini call failed after 3 attempts.*Persistent API Error",
            ):
                service.generate_event_draft(mock_game_state)

        # Should have tried 3 times
        assert mock_client.models.generate_content.call_count == 3

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_safety_block_raises_error(
        self, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test that safety-blocked responses raise error"""
        blocked_response = Mock()
        blocked_response.text = None  # Safety blocks return None

        mock_client = Mock()
        mock_client.models.generate_content.return_value = blocked_response
        mock_client_class.return_value = mock_client

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with patch("conestoga.services.gemini_event_service.uuid.uuid4", return_value="test-uuid"):
            with pytest.raises(GeminiEventServiceError, match="possibly safety-blocked"):
                service.generate_event_draft(mock_game_state)


class TestPromptBuilders:
    """Tests for prompt building methods"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_draft_prompt_includes_constraints(
        self, mock_client_class, service_config, mock_api_key, mock_game_state
    ):
        """Test draft prompt includes proper constraints"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        prompt = service._build_draft_prompt("test-event-id", mock_game_state)

        assert "test-event-id" in prompt
        assert "2-4" in prompt  # Choice count constraint
        assert "food" in prompt  # Allowed resource keys
        assert "shovel" in prompt  # Allowed item IDs
        assert "Independence, Missouri" in prompt  # Game state location

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_resolution_prompt_includes_draft_and_choice(
        self, mock_client_class, service_config, mock_api_key, mock_game_state, mock_event_draft
    ):
        """Test resolution prompt includes draft and choice"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        rng = {"roll": 50}
        prompt = service._build_resolution_prompt(
            "test-event-123", "A", mock_event_draft, mock_game_state, rng
        )

        assert "test-event-123" in prompt
        assert "A" in prompt  # choice_id
        assert "River Crossing" in prompt  # Draft title
        assert "50" in prompt  # RNG value

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_draft_prompt_limits_recent_log(
        self, mock_client_class, service_config, mock_api_key
    ):
        """Test that draft prompt only includes last 6 log entries"""
        large_log = [f"Log entry {i}" for i in range(20)]
        game_state = {
            "date": "1848-04-15",
            "location": "Test",
            "miles_traveled": 0,
            "season": "spring",
            "party": [],
            "resources": {},
            "inventory": [],
            "flags": [],
            "recent_log": large_log,
        }

        service = GeminiEventService(service_config, api_key=mock_api_key)
        prompt = service._build_draft_prompt("test-id", game_state)

        # Should only include last 6 entries
        assert "Log entry 14" in prompt
        assert "Log entry 19" in prompt
        assert "Log entry 0" not in prompt
        assert "Log entry 13" not in prompt


class TestServiceLifecycle:
    """Tests for service lifecycle methods"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_close_method(self, mock_client_class, service_config, mock_api_key):
        """Test close method can be called without error"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        # Should not raise any exception
        service.close()
