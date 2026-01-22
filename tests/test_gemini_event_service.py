"""Tests for GeminiEventService"""
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from conestoga.models.events import (
    DraftSchemaVersion,
    Effect,
    EffectOp,
    EventChoice,
    EventDraft,
    EventResolution,
    EventType,
    Requirement,
    RequirementType,
    ResolutionSchemaVersion,
    ResourceKey,
    RiskLevel,
)
from conestoga.services.gemini_event_service import (
    GeminiEventService,
    GeminiEventServiceConfig,
    GeminiEventServiceError,
)


@pytest.fixture
def mock_genai_client():
    """Mock genai.Client for testing"""
    with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def service_config():
    """Create a test service configuration"""
    return GeminiEventServiceConfig(
        model="gemini-3-flash-preview",
        thinking_level="low",
        max_output_tokens=2048,
        max_attempts=3,
        initial_backoff_s=0.1,  # Shorter for tests
    )


@pytest.fixture
def gemini_service(service_config, mock_genai_client):
    """Create a GeminiEventService instance with mocked client"""
    return GeminiEventService(cfg=service_config, api_key="test_api_key")


@pytest.fixture
def sample_game_state():
    """Sample game state for testing"""
    return {
        "date": "April 15, 1848",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "health": 100, "role": "leader"},
            {"name": "Mary", "health": 95, "role": "cook"},
        ],
        "resources": {"food": 500, "ammo": 100, "money": 200},
        "inventory": [{"item_id": "rifle", "quantity": 2}],
        "flags": ["game_started"],
        "recent_log": ["Started journey from Independence"],
    }


@pytest.fixture
def sample_event_draft():
    """Sample EventDraft for testing"""
    return EventDraft(
        schema_version=DraftSchemaVersion.V1,
        event_id="test-event-123",
        title="River Crossing",
        event_type=EventType.HAZARD,
        scene_text="You approach a wide river. The current looks swift.",
        choices=[
            EventChoice(
                choice_id="A",
                label="Ford the river",
                prompt="Attempt to cross directly through the water",
                risk=RiskLevel.HIGH,
                requirements=[],
            ),
            EventChoice(
                choice_id="B",
                label="Pay for ferry",
                prompt="Pay $50 to use the ferry",
                risk=RiskLevel.LOW,
                requirements=[
                    Requirement(
                        requirement_type=RequirementType.RESOURCE_AT_LEAST,
                        ui_text="Need at least $50",
                        resource=ResourceKey.MONEY,
                        min_value=50,
                    )
                ],
            ),
        ],
        safety_warnings=[],
        debug_tags=["water", "crossing"],
    )


@pytest.fixture
def sample_event_resolution():
    """Sample EventResolution for testing"""
    return EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id="test-event-123",
        choice_id="A",
        outcome_title="Successful Crossing",
        outcome_text="You ford the river successfully, though some supplies got wet.",
        effects=[
            Effect(
                op=EffectOp.DELTA_RESOURCE,
                note="Food damaged by water",
                resource=ResourceKey.FOOD,
                delta=-20,
            )
        ],
    )


class TestGeminiEventServiceConfig:
    """Tests for GeminiEventServiceConfig"""

    def test_config_initialization(self):
        """Test that config initializes with correct defaults"""
        config = GeminiEventServiceConfig()
        assert config.model == os.getenv("GEMINI_MODEL_ID", "gemini-3-flash-preview")
        assert config.thinking_level == "low"
        assert config.max_output_tokens == 2048
        assert config.max_attempts == 3
        assert config.initial_backoff_s == 0.6

    def test_config_custom_values(self):
        """Test that config accepts custom values"""
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
        """Test that config validates model is non-empty"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="")

    def test_config_validation_whitespace_model(self):
        """Test that config rejects whitespace-only model"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="   ")


class TestGeminiEventServiceInitialization:
    """Tests for GeminiEventService initialization"""

    def test_service_initialization_with_api_key(self, service_config):
        """Test service initializes with API key"""
        with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client_class:
            service = GeminiEventService(cfg=service_config, api_key="test_key")
            mock_client_class.assert_called_once_with(api_key="test_key")
            assert service.cfg == service_config

    def test_service_initialization_without_api_key(self, service_config):
        """Test service initializes without API key (uses env)"""
        with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client_class:
            service = GeminiEventService(cfg=service_config, api_key=None)
            mock_client_class.assert_called_once_with()
            assert service.cfg == service_config

    def test_service_has_safety_settings(self, gemini_service):
        """Test that service initializes with safety settings"""
        assert gemini_service.safety_settings is not None
        assert len(gemini_service.safety_settings) == 4


class TestGenerateEventDraft:
    """Tests for generate_event_draft method"""

    def test_generate_event_draft_success(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test successful event draft generation"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        # Call the method
        result = gemini_service.generate_event_draft(sample_game_state)

        # Verify the result
        assert isinstance(result, EventDraft)
        assert result.event_id is not None
        assert result.title == "River Crossing"
        assert result.event_type == EventType.HAZARD
        assert len(result.choices) == 2

        # Verify the API was called correctly
        mock_genai_client.models.generate_content.assert_called_once()

    def test_generate_event_draft_includes_game_state(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test that game state is included in the prompt"""
        mock_response = MagicMock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        gemini_service.generate_event_draft(sample_game_state)

        # Get the prompt that was passed
        call_args = mock_genai_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]

        # Verify key game state elements are in the prompt
        assert "Independence, Missouri" in prompt
        assert "April 15, 1848" in prompt

    def test_generate_event_draft_generates_uuid(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test that a UUID is generated for the event"""
        mock_response = MagicMock()
        # Use a dynamic event_id
        sample_event_draft_dict = sample_event_draft.model_dump()
        
        def generate_with_uuid(*args, **kwargs):
            # Extract UUID from prompt
            prompt = kwargs.get("contents", "")
            import re
            match = re.search(r"event_id MUST be exactly: ([a-f0-9-]+)", prompt)
            if match:
                sample_event_draft_dict["event_id"] = match.group(1)
            response = MagicMock()
            response.text = json.dumps(sample_event_draft_dict)
            return response

        mock_genai_client.models.generate_content.side_effect = generate_with_uuid

        result = gemini_service.generate_event_draft({})
        
        # Verify UUID format
        import uuid
        try:
            uuid.UUID(result.event_id)
        except ValueError:
            pytest.fail("event_id is not a valid UUID")


class TestResolveEvent:
    """Tests for resolve_event method"""

    def test_resolve_event_success(
        self,
        gemini_service,
        mock_genai_client,
        sample_event_draft,
        sample_event_resolution,
        sample_game_state,
    ):
        """Test successful event resolution"""
        mock_response = MagicMock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        result = gemini_service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        assert isinstance(result, EventResolution)
        assert result.event_id == "test-event-123"
        assert result.choice_id == "A"
        assert result.outcome_title == "Successful Crossing"
        assert len(result.effects) == 1

    def test_resolve_event_includes_draft_context(
        self,
        gemini_service,
        mock_genai_client,
        sample_event_draft,
        sample_event_resolution,
        sample_game_state,
    ):
        """Test that draft context is included in resolution prompt"""
        mock_response = MagicMock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        gemini_service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        call_args = mock_genai_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]

        # Verify draft info is in the prompt
        assert "test-event-123" in prompt
        assert "River Crossing" in prompt

    def test_resolve_event_with_rng(
        self,
        gemini_service,
        mock_genai_client,
        sample_event_draft,
        sample_event_resolution,
        sample_game_state,
    ):
        """Test that RNG data is included when provided"""
        mock_response = MagicMock()
        mock_response.text = sample_event_resolution.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        rng_data = {"roll": 75, "success_threshold": 50}
        gemini_service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
            rng=rng_data,
        )

        call_args = mock_genai_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]

        # Verify RNG data is in the prompt
        assert "75" in prompt


class TestValidationAndRepair:
    """Tests for validation and repair logic"""

    def test_validation_error_triggers_repair(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test that validation errors trigger repair"""
        # First response has invalid JSON
        invalid_response = MagicMock()
        invalid_response.text = '{"event_id": "test", "invalid": true}'

        # Second response (repair) is valid
        valid_response = MagicMock()
        valid_response.text = sample_event_draft.model_dump_json()

        mock_genai_client.models.generate_content.side_effect = [
            invalid_response,
            valid_response,
        ]

        result = gemini_service.generate_event_draft({})

        # Verify repair was called (2 API calls)
        assert mock_genai_client.models.generate_content.call_count == 2
        assert isinstance(result, EventDraft)

    def test_repair_json_success(self, gemini_service, mock_genai_client, sample_event_draft):
        """Test successful JSON repair"""
        # Mock a successful repair
        mock_response = MagicMock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        result = gemini_service._repair_json(
            schema_model=EventDraft,
            raw_text='{"bad": "json"}',
            error="Missing required field 'event_id'",
        )

        assert isinstance(result, EventDraft)
        mock_genai_client.models.generate_content.assert_called_once()

    def test_repair_json_empty_response(self, gemini_service, mock_genai_client):
        """Test repair fails with empty response"""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Repair call returned empty response"):
            gemini_service._repair_json(
                schema_model=EventDraft,
                raw_text='{"bad": "json"}',
                error="Some error",
            )

    def test_repair_json_validation_still_fails(self, gemini_service, mock_genai_client):
        """Test repair that still returns invalid JSON"""
        mock_response = MagicMock()
        mock_response.text = '{"still": "invalid"}'
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValidationError):
            gemini_service._repair_json(
                schema_model=EventDraft,
                raw_text='{"bad": "json"}',
                error="Some error",
            )


class TestErrorHandling:
    """Tests for error handling scenarios"""

    def test_empty_response_raises_error(self, gemini_service, mock_genai_client):
        """Test that empty response raises GeminiEventServiceError"""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Empty response text"):
            gemini_service.generate_event_draft({})

    def test_none_response_text_raises_error(self, gemini_service, mock_genai_client):
        """Test that None response text raises error"""
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Empty response text"):
            gemini_service.generate_event_draft({})

    def test_retry_on_api_error(self, gemini_service, mock_genai_client, sample_event_draft):
        """Test retry logic on API errors"""
        # First attempt fails, second succeeds
        mock_response = MagicMock()
        mock_response.text = sample_event_draft.model_dump_json()

        mock_genai_client.models.generate_content.side_effect = [
            Exception("API Error"),
            mock_response,
        ]

        result = gemini_service.generate_event_draft({})

        assert isinstance(result, EventDraft)
        assert mock_genai_client.models.generate_content.call_count == 2

    def test_max_retries_exceeded(self, gemini_service, mock_genai_client):
        """Test that max retries are respected"""
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")

        with pytest.raises(GeminiEventServiceError, match="failed after 3 attempts"):
            gemini_service.generate_event_draft({})

        assert mock_genai_client.models.generate_content.call_count == 3

    def test_retry_with_exponential_backoff(self, gemini_service, mock_genai_client):
        """Test that backoff increases exponentially"""
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")

        with patch("conestoga.services.gemini_event_service.time.sleep") as mock_sleep:
            with pytest.raises(GeminiEventServiceError):
                gemini_service.generate_event_draft({})

            # Verify backoff increased
            assert mock_sleep.call_count == 2  # 3 attempts = 2 sleeps
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert calls[1] > calls[0]  # Second backoff is longer

    def test_validation_error_during_repair_propagates(
        self, gemini_service, mock_genai_client
    ):
        """Test that validation errors during repair are propagated as GeminiEventServiceError"""
        # First call returns invalid JSON
        invalid_response = MagicMock()
        invalid_response.text = '{"invalid": true}'

        # Repair also returns invalid JSON
        invalid_repair_response = MagicMock()
        invalid_repair_response.text = '{"still_invalid": true}'

        mock_genai_client.models.generate_content.side_effect = [
            invalid_response,
            invalid_repair_response,
        ]

        # Validation error is wrapped in GeminiEventServiceError after all retries fail
        with pytest.raises(GeminiEventServiceError):
            gemini_service.generate_event_draft({})


class TestPromptBuilders:
    """Tests for prompt building methods"""

    def test_build_draft_prompt_includes_constraints(self, gemini_service):
        """Test that draft prompt includes all necessary constraints"""
        game_state = {
            "date": "May 1, 1848",
            "location": "Kansas River",
            "miles_traveled": 100,
        }

        prompt = gemini_service._build_draft_prompt(
            event_id="test-123", game_state=game_state
        )

        assert "test-123" in prompt
        assert "May 1, 1848" in prompt
        assert "Kansas River" in prompt
        assert "choices MUST be 2-4" in prompt

    def test_build_draft_prompt_includes_allowed_resources(self, gemini_service):
        """Test that draft prompt includes allowed resource keys"""
        prompt = gemini_service._build_draft_prompt(event_id="test", game_state={})

        assert "food" in prompt
        assert "ammo" in prompt
        assert "money" in prompt

    def test_build_resolution_prompt_includes_all_context(
        self, gemini_service, sample_event_draft, sample_game_state
    ):
        """Test that resolution prompt includes all necessary context"""
        prompt = gemini_service._build_resolution_prompt(
            event_id="test-123",
            choice_id="A",
            draft=sample_event_draft,
            game_state=sample_game_state,
            rng={"roll": 50},
        )

        assert "test-123" in prompt
        assert "choice_id MUST be exactly: A" in prompt
        assert "River Crossing" in prompt
        assert "Independence, Missouri" in prompt
        assert "50" in prompt  # RNG value


class TestSafetySettings:
    """Tests for safety settings"""

    def test_default_safety_settings(self, gemini_service):
        """Test that default safety settings are configured"""
        settings = gemini_service._default_safety_settings()

        assert len(settings) == 4
        
        # Verify categories are covered
        from google.genai import types
        categories = {s.category for s in settings}
        assert types.HarmCategory.HARM_CATEGORY_HATE_SPEECH in categories
        assert types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in categories
        assert types.HarmCategory.HARM_CATEGORY_HARASSMENT in categories
        assert types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in categories

    def test_safety_settings_used_in_api_call(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test that safety settings are passed to API calls"""
        mock_response = MagicMock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        gemini_service.generate_event_draft({})

        call_args = mock_genai_client.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config.safety_settings == gemini_service.safety_settings


class TestServiceClose:
    """Tests for service cleanup"""

    def test_close_method_exists(self, gemini_service):
        """Test that close method can be called without error"""
        # Should not raise any exception
        gemini_service.close()
