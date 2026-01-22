"""Tests for GeminiEventService"""
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from pydantic import ValidationError

from conestoga.services.gemini_event_service import (
    GeminiEventService,
    GeminiEventServiceConfig,
    GeminiEventServiceError,
)
from conestoga.models.events import (
    EventDraft,
    EventResolution,
    EventChoice,
    EventType,
    RiskLevel,
    DraftSchemaVersion,
    ResolutionSchemaVersion,
)


@pytest.fixture
def service_config():
    """Create a default service configuration for testing"""
    return GeminiEventServiceConfig(
        model="gemini-3-flash-preview",
        thinking_level="low",
        max_output_tokens=2048,
        max_attempts=3,
        initial_backoff_s=0.1,  # Shorter for testing
    )


@pytest.fixture
def mock_client():
    """Create a mock Gemini client"""
    client = Mock()
    client.models = Mock()
    return client


@pytest.fixture
def service(service_config, mock_client):
    """Create a GeminiEventService instance with mocked client"""
    with patch('conestoga.services.gemini_event_service.genai.Client') as mock_genai:
        mock_genai.return_value = mock_client
        service = GeminiEventService(service_config, api_key="test_key")
        service.client = mock_client
        return service


@pytest.fixture
def sample_game_state():
    """Create a sample game state for testing"""
    return {
        "date": "1848-04-15",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "health": 100, "role": "guide"},
            {"name": "Mary", "health": 95, "role": "doctor"},
        ],
        "resources": {
            "food": 200,
            "ammo": 50,
            "money": 100,
            "medicine": 10,
            "clothing": 20,
            "oxen": 4,
            "wagon_parts": 3,
        },
        "inventory": [
            {"item_id": "shovel", "quantity": 1},
            {"item_id": "rope", "quantity": 2},
        ],
        "flags": ["just_started"],
        "recent_log": [
            "Started journey from Independence",
        ],
    }


@pytest.fixture
def sample_event_draft():
    """Create a sample EventDraft for testing"""
    return EventDraft(
        schema_version=DraftSchemaVersion.V1,
        event_id="test-event-123",
        title="River Crossing",
        event_type=EventType.HAZARD,
        scene_text="You arrive at a wide river. The current is swift.",
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
                label="Take the ferry",
                prompt="Pay to use the ferry",
                risk=RiskLevel.LOW,
                requirements=[],
            ),
        ],
        safety_warnings=[],
        debug_tags=["river", "crossing"],
    )


@pytest.fixture
def sample_event_resolution():
    """Create a sample EventResolution for testing"""
    return EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id="test-event-123",
        choice_id="A",
        outcome_title="Crossed Successfully",
        outcome_text="You made it across with some difficulty.",
        effects=[],
    )


class TestGeminiEventServiceInit:
    """Tests for service initialization"""

    def test_init_with_api_key(self, service_config):
        """Test initialization with explicit API key"""
        with patch('conestoga.services.gemini_event_service.genai.Client') as mock_genai:
            service = GeminiEventService(service_config, api_key="test_key")
            mock_genai.assert_called_once_with(api_key="test_key")

    def test_init_without_api_key(self, service_config):
        """Test initialization without explicit API key (uses environment)"""
        with patch('conestoga.services.gemini_event_service.genai.Client') as mock_genai:
            service = GeminiEventService(service_config)
            mock_genai.assert_called_once_with()

    def test_safety_settings_configured(self, service, service_config):
        """Test that safety settings are properly configured"""
        assert service.safety_settings is not None
        assert len(service.safety_settings) == 4  # Should have 4 safety categories

    def test_config_stored(self, service, service_config):
        """Test that configuration is stored correctly"""
        assert service.cfg == service_config


class TestGenerateEventDraft:
    """Tests for generate_event_draft method"""

    def test_generate_event_draft_success(self, service, mock_client, sample_game_state, sample_event_draft):
        """Test successful event draft generation"""
        # Mock the API response
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        result = service.generate_event_draft(sample_game_state)

        assert isinstance(result, EventDraft)
        assert result.title == "River Crossing"
        assert result.event_type == EventType.HAZARD
        assert len(result.choices) == 2

    def test_generate_event_draft_prompt_contains_game_state(self, service, mock_client, sample_game_state):
        """Test that the prompt includes relevant game state"""
        mock_response = Mock()
        # Create a valid EventDraft response
        draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-id",
            title="Test",
            event_type=EventType.HAZARD,
            scene_text="Test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Choice A",
                    prompt="Do something",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response.text = draft.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        service.generate_event_draft(sample_game_state)

        # Verify the prompt was generated and passed
        assert mock_client.models.generate_content.called
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]['contents']
        
        # Check that key game state elements are in the prompt
        assert "Independence, Missouri" in prompt or "location" in prompt.lower()

    def test_generate_event_draft_generates_unique_event_id(self, service, mock_client, sample_game_state):
        """Test that each call generates a unique event ID"""
        mock_response = Mock()
        
        def create_draft_with_id(event_id):
            return EventDraft(
                schema_version=DraftSchemaVersion.V1,
                event_id=event_id,
                title="Test",
                event_type=EventType.HAZARD,
                scene_text="Test",
                choices=[
                    EventChoice(
                        choice_id="A",
                        label="A",
                        prompt="Do A",
                        risk=RiskLevel.LOW,
                        requirements=[],
                    )
                ],
                safety_warnings=[],
                debug_tags=[],
            )

        # Track event IDs returned
        event_ids = []
        
        def mock_generate(*args, **kwargs):
            # Extract event_id from the prompt
            prompt = kwargs['contents']
            import re
            match = re.search(r'event_id MUST be exactly: ([a-f0-9\-]+)', prompt)
            if match:
                event_id = match.group(1)
                event_ids.append(event_id)
                mock_resp = Mock()
                mock_resp.text = create_draft_with_id(event_id).model_dump_json()
                return mock_resp
            return Mock()

        mock_client.models.generate_content.side_effect = mock_generate

        result1 = service.generate_event_draft(sample_game_state)
        result2 = service.generate_event_draft(sample_game_state)

        # Each call should generate a different UUID
        assert len(event_ids) == 2
        assert event_ids[0] != event_ids[1]


class TestResolveEvent:
    """Tests for resolve_event method"""

    def test_resolve_event_success(self, service, mock_client, sample_event_draft, sample_game_state, sample_event_resolution):
        """Test successful event resolution"""
        mock_response = Mock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        result = service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        assert isinstance(result, EventResolution)
        assert result.event_id == "test-event-123"
        assert result.choice_id == "A"

    def test_resolve_event_with_rng(self, service, mock_client, sample_event_draft, sample_game_state, sample_event_resolution):
        """Test event resolution with RNG inputs"""
        mock_response = Mock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        rng = {"roll": 75, "success": True}
        result = service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
            rng=rng,
        )

        assert isinstance(result, EventResolution)
        
        # Verify RNG was passed in the prompt
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]['contents']
        assert "RNG" in prompt or "rng" in prompt.lower()

    def test_resolve_event_prompt_contains_draft_and_choice(self, service, mock_client, sample_event_draft, sample_game_state, sample_event_resolution):
        """Test that resolution prompt includes draft and choice info"""
        mock_response = Mock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]['contents']
        
        # Verify key elements are in prompt
        assert "test-event-123" in prompt  # event_id
        assert "A" in prompt or "choice_id" in prompt.lower()


class TestValidationAndRepair:
    """Tests for validation and repair logic"""

    def test_validation_success_no_repair_needed(self, service, mock_client, sample_game_state, sample_event_draft):
        """Test that valid JSON doesn't trigger repair"""
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        result = service.generate_event_draft(sample_game_state)

        # Should only be called once (no repair call)
        assert mock_client.models.generate_content.call_count == 1

    def test_validation_triggers_repair_on_invalid_json(self, service, mock_client, sample_game_state, sample_event_draft):
        """Test that invalid JSON triggers repair logic"""
        # First response: invalid (missing required field)
        invalid_response = Mock()
        invalid_json = {
            "schema_version": "event_draft.v1",
            "event_id": "test-123",
            # Missing other required fields
        }
        invalid_response.text = json.dumps(invalid_json)

        # Second response (repair): valid
        valid_response = Mock()
        valid_response.text = sample_event_draft.model_dump_json()

        mock_client.models.generate_content.side_effect = [invalid_response, valid_response]

        result = service.generate_event_draft(sample_game_state)

        # Should be called twice (initial + repair)
        assert mock_client.models.generate_content.call_count == 2
        assert isinstance(result, EventDraft)

    def test_repair_json_success(self, service, mock_client, sample_event_draft):
        """Test successful JSON repair"""
        invalid_json = '{"incomplete": "data"}'
        error_msg = "Validation error: missing required fields"

        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        result = service._repair_json(EventDraft, invalid_json, error_msg)

        assert isinstance(result, EventDraft)
        # Verify repair prompt was sent
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]['contents']
        assert "validation" in prompt.lower() or "error" in prompt.lower()

    def test_repair_json_empty_response_raises_error(self, service, mock_client):
        """Test that empty repair response raises error"""
        mock_response = Mock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Repair call returned empty response"):
            service._repair_json(EventDraft, '{"bad": "json"}', "error")


class TestErrorHandling:
    """Tests for error handling scenarios"""

    def test_empty_response_raises_error(self, service, mock_client, sample_game_state):
        """Test that empty response (safety blocked) raises error"""
        mock_response = Mock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Empty response text"):
            service.generate_event_draft(sample_game_state)

    def test_retry_on_api_error(self, service, mock_client, sample_game_state, sample_event_draft):
        """Test retry logic on API errors"""
        # First two calls fail, third succeeds
        error1 = Exception("API error 1")
        error2 = Exception("API error 2")
        success_response = Mock()
        success_response.text = sample_event_draft.model_dump_json()

        mock_client.models.generate_content.side_effect = [error1, error2, success_response]

        result = service.generate_event_draft(sample_game_state)

        # Should have been called 3 times
        assert mock_client.models.generate_content.call_count == 3
        assert isinstance(result, EventDraft)

    def test_max_retries_exceeded_raises_error(self, service, mock_client, sample_game_state):
        """Test that exceeding max retries raises error"""
        # All calls fail
        mock_client.models.generate_content.side_effect = Exception("Persistent error")

        with pytest.raises(GeminiEventServiceError, match="Gemini call failed after .* attempts"):
            service.generate_event_draft(sample_game_state)

        # Should have been called max_attempts times
        assert mock_client.models.generate_content.call_count == service.cfg.max_attempts

    def test_retry_with_exponential_backoff(self, service, mock_client, sample_game_state, sample_event_draft):
        """Test that retries use exponential backoff"""
        with patch('conestoga.services.gemini_event_service.time.sleep') as mock_sleep:
            # First two calls fail, third succeeds
            error = Exception("Temporary error")
            success_response = Mock()
            success_response.text = sample_event_draft.model_dump_json()

            mock_client.models.generate_content.side_effect = [error, error, success_response]

            service.generate_event_draft(sample_game_state)

            # Should have slept twice (after first two failures)
            assert mock_sleep.call_count == 2
            
            # Verify exponential backoff (each sleep should be longer)
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls[0] == service.cfg.initial_backoff_s
            assert sleep_calls[1] == service.cfg.initial_backoff_s * 1.8


class TestSafetySettings:
    """Tests for safety settings configuration"""

    def test_safety_settings_has_all_categories(self, service):
        """Test that all safety categories are configured"""
        from google.genai import types
        
        safety_settings = service._default_safety_settings()
        
        categories = {setting.category for setting in safety_settings}
        
        # Should have 4 harm categories
        assert types.HarmCategory.HARM_CATEGORY_HATE_SPEECH in categories
        assert types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in categories
        assert types.HarmCategory.HARM_CATEGORY_HARASSMENT in categories
        assert types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in categories

    def test_safety_settings_thresholds(self, service):
        """Test that safety thresholds are properly configured"""
        from google.genai import types
        
        safety_settings = service._default_safety_settings()
        settings_dict = {setting.category: setting.threshold for setting in safety_settings}
        
        # Hate speech and sexually explicit should block low and above
        assert settings_dict[types.HarmCategory.HARM_CATEGORY_HATE_SPEECH] == \
            types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        assert settings_dict[types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT] == \
            types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        
        # Harassment should block medium and above
        assert settings_dict[types.HarmCategory.HARM_CATEGORY_HARASSMENT] == \
            types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
        
        # Dangerous content should only block high
        assert settings_dict[types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT] == \
            types.HarmBlockThreshold.BLOCK_ONLY_HIGH


class TestPromptBuilding:
    """Tests for prompt building logic"""

    def test_build_draft_prompt_includes_constraints(self, service, sample_game_state):
        """Test that draft prompt includes all necessary constraints"""
        prompt = service._build_draft_prompt("test-event-id", sample_game_state)
        
        # Should include event_id
        assert "test-event-id" in prompt
        
        # Should include constraints
        assert "2-4" in prompt or "choices" in prompt.lower()
        
        # Should include allowed resources and items
        assert "food" in prompt.lower() or "resource" in prompt.lower()

    def test_build_draft_prompt_includes_recent_log(self, service, sample_game_state):
        """Test that draft prompt includes recent log entries"""
        sample_game_state["recent_log"] = ["Event 1", "Event 2", "Event 3"]
        
        prompt = service._build_draft_prompt("test-id", sample_game_state)
        
        # Should include recent log
        assert "Event 1" in prompt or "recent_log" in prompt.lower()

    def test_build_resolution_prompt_includes_draft(self, service, sample_event_draft, sample_game_state):
        """Test that resolution prompt includes draft information"""
        prompt = service._build_resolution_prompt(
            event_id="test-event-123",
            choice_id="A",
            draft=sample_event_draft,
            game_state=sample_game_state,
            rng={"roll": 50},
        )
        
        # Should include event and choice IDs
        assert "test-event-123" in prompt
        assert "A" in prompt
        
        # Should include draft title
        assert "River Crossing" in prompt or "title" in prompt.lower()
        
        # Should include RNG
        assert "50" in prompt or "rng" in prompt.lower()


class TestServiceConfiguration:
    """Tests for service configuration"""

    def test_default_config_values(self):
        """Test default configuration values"""
        config = GeminiEventServiceConfig()
        
        assert config.model == "gemini-3-flash-preview"
        assert config.thinking_level == "low"
        assert config.max_output_tokens == 2048
        assert config.max_attempts == 3
        assert config.initial_backoff_s == 0.6

    def test_custom_config_values(self):
        """Test custom configuration values"""
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

    def test_config_is_frozen(self):
        """Test that config dataclass is frozen (immutable)"""
        config = GeminiEventServiceConfig()
        
        with pytest.raises(Exception):  # FrozenInstanceError in dataclasses
            config.model = "new-model"


class TestServiceClose:
    """Tests for service cleanup"""

    def test_close_method_exists(self, service):
        """Test that close method exists and can be called"""
        # Should not raise any errors
        service.close()
        
    def test_close_is_safe_to_call_multiple_times(self, service):
        """Test that close can be called multiple times safely"""
        service.close()
        service.close()  # Should not raise
