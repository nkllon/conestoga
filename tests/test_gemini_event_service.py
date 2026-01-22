"""Tests for GeminiEventService"""
import json
import os
from unittest.mock import Mock, MagicMock, patch
import pytest
from pydantic import ValidationError

from conestoga.services.gemini_event_service import (
    GeminiEventService,
    GeminiEventServiceConfig,
    GeminiEventServiceError,
)
from conestoga.models.events import (
    EventDraft,
    EventResolution,
    EventType,
    RiskLevel,
    EventChoice,
    Effect,
    EffectOp,
    ResourceKey,
    DraftSchemaVersion,
    ResolutionSchemaVersion,
)


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing"""
    return "test-api-key-12345"


@pytest.fixture
def service_config():
    """Provide a default service config"""
    return GeminiEventServiceConfig(
        model="gemini-3-flash-preview",
        thinking_level="low",
        max_output_tokens=2048,
        max_attempts=3,
        initial_backoff_s=0.1,  # Faster for tests
    )


@pytest.fixture
def game_state():
    """Provide a sample game state"""
    return {
        "date": "1848-05-01",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "role": "leader", "health": 100},
            {"name": "Mary", "role": "doctor", "health": 100},
        ],
        "resources": {
            "food": 500,
            "ammo": 100,
            "money": 300,
            "medicine": 50,
            "clothing": 10,
            "oxen": 4,
            "wagon_parts": 5,
        },
        "inventory": [
            {"item_id": "shovel", "quantity": 1},
            {"item_id": "rope", "quantity": 2},
        ],
        "flags": ["tutorial_complete"],
        "recent_log": ["Started the journey", "Crossed the Missouri River"],
    }


@pytest.fixture
def sample_event_draft():
    """Provide a sample EventDraft"""
    return EventDraft(
        schema_version=DraftSchemaVersion.V1,
        event_id="test-event-123",
        title="River Crossing",
        event_type=EventType.HAZARD,
        scene_text="You approach a swollen river. The water looks dangerous.",
        choices=[
            EventChoice(
                choice_id="A",
                label="Ford the river",
                prompt="Try to cross directly through the water",
                risk=RiskLevel.HIGH,
                requirements=[],
            ),
            EventChoice(
                choice_id="B",
                label="Wait for better conditions",
                prompt="Camp here and wait for the water level to drop",
                risk=RiskLevel.LOW,
                requirements=[],
            ),
        ],
        safety_warnings=[],
        debug_tags=["river", "hazard"],
    )


@pytest.fixture
def sample_event_resolution():
    """Provide a sample EventResolution"""
    return EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id="test-event-123",
        choice_id="A",
        outcome_title="Successful Crossing",
        outcome_text="You ford the river successfully, though the wagon gets wet.",
        effects=[
            Effect(
                op=EffectOp.DELTA_RESOURCE,
                note="Water damaged some food supplies",
                resource=ResourceKey.FOOD,
                delta=-20,
            ),
        ],
    )


class TestGeminiEventServiceConfig:
    """Test GeminiEventServiceConfig validation and defaults"""

    def test_default_config(self):
        """Test default configuration values"""
        config = GeminiEventServiceConfig()
        assert config.model == os.getenv("GEMINI_MODEL_ID", "gemini-3-flash-preview")
        assert config.thinking_level == "low"
        assert config.max_output_tokens == 2048
        assert config.max_attempts == 3
        assert config.initial_backoff_s == 0.6

    def test_config_with_custom_values(self):
        """Test custom configuration values"""
        config = GeminiEventServiceConfig(
            model="gemini-pro",
            thinking_level="high",
            max_output_tokens=4096,
            max_attempts=5,
            initial_backoff_s=1.0,
        )
        assert config.model == "gemini-pro"
        assert config.thinking_level == "high"
        assert config.max_output_tokens == 4096
        assert config.max_attempts == 5
        assert config.initial_backoff_s == 1.0

    def test_config_validation_empty_model(self):
        """Test that empty model string raises ValueError"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="")

    def test_config_validation_whitespace_model(self):
        """Test that whitespace-only model string raises ValueError"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="   ")


class TestGeminiEventServiceInitialization:
    """Test GeminiEventService initialization"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_init_with_api_key(self, mock_client_class, service_config, mock_api_key):
        """Test initialization with explicit API key"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        mock_client_class.assert_called_once_with(api_key=mock_api_key)
        assert service.cfg == service_config

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_init_without_api_key(self, mock_client_class, service_config):
        """Test initialization without API key (uses env vars)"""
        service = GeminiEventService(service_config)
        mock_client_class.assert_called_once_with()
        assert service.cfg == service_config

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_safety_settings_configured(self, mock_client_class, service_config, mock_api_key):
        """Test that safety settings are configured on initialization"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        assert service.safety_settings is not None
        assert len(service.safety_settings) == 4  # 4 harm categories

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_close_method(self, mock_client_class, service_config, mock_api_key):
        """Test close method doesn't raise errors"""
        service = GeminiEventService(service_config, api_key=mock_api_key)
        service.close()  # Should not raise


class TestGenerateEventDraft:
    """Test generate_event_draft method"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_generate_event_draft_success(
        self, mock_client_class, service_config, mock_api_key, game_state, sample_event_draft
    ):
        """Test successful event draft generation"""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service.generate_event_draft(game_state)

        # Verify result
        assert isinstance(result, EventDraft)
        assert result.title == sample_event_draft.title
        assert result.event_type == sample_event_draft.event_type
        assert len(result.choices) >= 2

        # Verify the API was called
        mock_client.models.generate_content.assert_called_once()

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_generate_event_draft_with_uuid(
        self, mock_client_class, service_config, mock_api_key, game_state
    ):
        """Test that generated event has a valid UUID"""
        import uuid
        
        # Generate a real UUID for the test
        test_uuid = str(uuid.uuid4())
        
        # Create a minimal valid EventDraft with a proper UUID
        valid_draft_json = json.dumps({
            "schema_version": "event_draft.v1",
            "event_id": test_uuid,
            "title": "Test Event",
            "event_type": "hazard",
            "scene_text": "A test scene",
            "choices": [
                {
                    "choice_id": "A",
                    "label": "Choice A",
                    "prompt": "Do something",
                    "risk": "low",
                    "requirements": []
                }
            ],
            "safety_warnings": [],
            "debug_tags": []
        })
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = valid_draft_json
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service.generate_event_draft(game_state)

        # event_id should be a valid UUID format
        try:
            parsed_uuid = uuid.UUID(result.event_id)
            assert str(parsed_uuid) == result.event_id
        except ValueError:
            pytest.fail("event_id is not a valid UUID")

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_generate_event_draft_empty_response(
        self, mock_client_class, service_config, mock_api_key, game_state
    ):
        """Test handling of empty response (safety block)"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with pytest.raises(GeminiEventServiceError, match="Empty response text"):
            service.generate_event_draft(game_state)


class TestResolveEvent:
    """Test resolve_event method"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_resolve_event_success(
        self,
        mock_client_class,
        service_config,
        mock_api_key,
        game_state,
        sample_event_draft,
        sample_event_resolution,
    ):
        """Test successful event resolution"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service.resolve_event(sample_event_draft, "A", game_state)

        # Verify result
        assert isinstance(result, EventResolution)
        assert result.event_id == sample_event_draft.event_id
        assert result.choice_id == "A"
        assert result.outcome_title == sample_event_resolution.outcome_title

        # Verify API was called
        mock_client.models.generate_content.assert_called_once()

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_resolve_event_with_rng(
        self,
        mock_client_class,
        service_config,
        mock_api_key,
        game_state,
        sample_event_draft,
        sample_event_resolution,
    ):
        """Test event resolution with custom RNG"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)
        rng_data = {"dice_roll": 15, "success": True}
        result = service.resolve_event(sample_event_draft, "A", game_state, rng=rng_data)

        assert isinstance(result, EventResolution)
        assert result.event_id == sample_event_draft.event_id


class TestValidationAndRepair:
    """Test validation logic and repair_json method"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_validation_error_triggers_repair(
        self, mock_client_class, service_config, mock_api_key, game_state, sample_event_draft
    ):
        """Test that validation errors trigger repair loop"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First call returns invalid JSON, second call (repair) returns valid JSON
        invalid_json = '{"invalid": "structure"}'
        valid_json = sample_event_draft.model_dump_json()

        mock_response1 = Mock()
        mock_response1.text = invalid_json
        mock_response2 = Mock()
        mock_response2.text = valid_json

        mock_client.models.generate_content.side_effect = [mock_response1, mock_response2]

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service.generate_event_draft(game_state)

        # Should succeed after repair
        assert isinstance(result, EventDraft)
        # Verify repair was called (2 API calls total)
        assert mock_client.models.generate_content.call_count == 2

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_repair_json_success(
        self, mock_client_class, service_config, mock_api_key, sample_event_draft
    ):
        """Test successful JSON repair"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Setup repair response
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)

        # Call repair directly
        result = service._repair_json(
            EventDraft,
            raw_text='{"invalid": "json"}',
            error="Validation error: missing required fields",
        )

        assert isinstance(result, EventDraft)
        mock_client.models.generate_content.assert_called_once()

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_repair_json_empty_response(self, mock_client_class, service_config, mock_api_key):
        """Test repair with empty response raises error"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with pytest.raises(GeminiEventServiceError, match="Repair call returned empty response"):
            service._repair_json(EventDraft, raw_text='{"invalid": "json"}', error="test error")


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_max_retries_exceeded(self, mock_client_class, service_config, mock_api_key, game_state):
        """Test that max retries are respected"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Make all attempts fail
        mock_client.models.generate_content.side_effect = Exception("API Error")

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with pytest.raises(GeminiEventServiceError, match="failed after 3 attempts"):
            service.generate_event_draft(game_state)

        # Should have attempted max_attempts times
        assert mock_client.models.generate_content.call_count == service_config.max_attempts

    @patch("conestoga.services.gemini_event_service.genai.Client")
    @patch("time.sleep")  # Mock sleep to speed up test
    def test_exponential_backoff(
        self, mock_sleep, mock_client_class, service_config, mock_api_key, game_state, sample_event_draft
    ):
        """Test exponential backoff on retries"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First two attempts fail, third succeeds
        mock_client.models.generate_content.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Mock(text=sample_event_draft.model_dump_json()),
        ]

        service = GeminiEventService(service_config, api_key=mock_api_key)
        result = service.generate_event_draft(game_state)

        # Should succeed on third attempt
        assert isinstance(result, EventDraft)

        # Verify backoff timing
        assert mock_sleep.call_count == 2
        # First backoff: initial_backoff_s
        assert mock_sleep.call_args_list[0][0][0] == pytest.approx(0.1, rel=0.01)
        # Second backoff: initial_backoff_s * 1.8
        assert mock_sleep.call_args_list[1][0][0] == pytest.approx(0.18, rel=0.01)

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_network_error_handling(
        self, mock_client_class, service_config, mock_api_key, game_state
    ):
        """Test handling of network errors"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate network error
        mock_client.models.generate_content.side_effect = ConnectionError("Network unreachable")

        service = GeminiEventService(service_config, api_key=mock_api_key)

        with pytest.raises(GeminiEventServiceError):
            service.generate_event_draft(game_state)

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_malformed_json_after_repair_fails(
        self, mock_client_class, service_config, mock_api_key, game_state
    ):
        """Test that repair failure propagates error"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Both initial and repair calls return invalid JSON
        invalid_json = '{"invalid": "structure"}'
        mock_response1 = Mock()
        mock_response1.text = invalid_json
        mock_response2 = Mock()
        mock_response2.text = invalid_json

        # The service will retry max_attempts times, and each time it tries to repair
        # So we need to provide enough responses
        mock_client.models.generate_content.side_effect = [
            mock_response1, mock_response2,  # First attempt + repair
            mock_response1, mock_response2,  # Second attempt + repair
            mock_response1, mock_response2,  # Third attempt + repair
        ]

        service = GeminiEventService(service_config, api_key=mock_api_key)

        # After all retries fail, it should raise GeminiEventServiceError
        with pytest.raises(GeminiEventServiceError):
            service.generate_event_draft(game_state)


class TestPromptBuilders:
    """Test prompt building methods"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_build_draft_prompt_includes_game_state(
        self, mock_client_class, service_config, mock_api_key, game_state
    ):
        """Test that draft prompt includes relevant game state"""
        service = GeminiEventService(service_config, api_key=mock_api_key)

        prompt = service._build_draft_prompt(event_id="test-123", game_state=game_state)

        # Verify key elements are in the prompt
        assert "test-123" in prompt
        assert "Independence, Missouri" in prompt
        assert "food" in prompt.lower()
        assert "500" in prompt  # food amount

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_build_resolution_prompt_includes_choice(
        self, mock_client_class, service_config, mock_api_key, game_state, sample_event_draft
    ):
        """Test that resolution prompt includes choice information"""
        service = GeminiEventService(service_config, api_key=mock_api_key)

        prompt = service._build_resolution_prompt(
            event_id=sample_event_draft.event_id,
            choice_id="A",
            draft=sample_event_draft,
            game_state=game_state,
            rng={"dice_roll": 15},
        )

        # Verify key elements
        assert sample_event_draft.event_id in prompt
        assert "A" in prompt
        assert "dice_roll" in prompt
        assert "15" in prompt

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_draft_prompt_limits_recent_log(
        self, mock_client_class, service_config, mock_api_key
    ):
        """Test that draft prompt limits recent log to 6 entries"""
        game_state_with_long_log = {
            "date": "1848-05-01",
            "location": "Test",
            "recent_log": [f"Event {i}" for i in range(20)],  # 20 entries
            "resources": {},
        }

        service = GeminiEventService(service_config, api_key=mock_api_key)
        prompt = service._build_draft_prompt(event_id="test-123", game_state=game_state_with_long_log)

        # Check that only last 6 entries are included
        log_entries = [f"Event {i}" for i in range(14, 20)]
        for entry in log_entries:
            assert entry in prompt

        # Earlier entries should not be in prompt
        assert "Event 0" not in prompt
        assert "Event 5" not in prompt


class TestSafetySettings:
    """Test safety settings configuration"""

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_safety_settings_include_all_categories(
        self, mock_client_class, service_config, mock_api_key
    ):
        """Test that all harm categories are configured"""
        service = GeminiEventService(service_config, api_key=mock_api_key)

        settings = service._default_safety_settings()

        # Should have 4 categories
        assert len(settings) == 4

        # Verify all categories are present
        from google.genai import types
        categories = {setting.category for setting in settings}
        assert types.HarmCategory.HARM_CATEGORY_HATE_SPEECH in categories
        assert types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in categories
        assert types.HarmCategory.HARM_CATEGORY_HARASSMENT in categories
        assert types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in categories

    @patch("conestoga.services.gemini_event_service.genai.Client")
    def test_safety_thresholds_appropriate(
        self, mock_client_class, service_config, mock_api_key
    ):
        """Test that safety thresholds are set appropriately"""
        service = GeminiEventService(service_config, api_key=mock_api_key)

        settings = service._default_safety_settings()
        settings_dict = {setting.category: setting.threshold for setting in settings}

        from google.genai import types

        # Verify strict thresholds for sensitive categories
        assert (
            settings_dict[types.HarmCategory.HARM_CATEGORY_HATE_SPEECH]
            == types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        )
        assert (
            settings_dict[types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT]
            == types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        )
