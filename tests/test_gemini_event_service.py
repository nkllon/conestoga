"""Comprehensive tests for GeminiEventService"""
import json
import os
from typing import Any, Dict
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


# ------------------------------
# Fixtures
# ------------------------------


@pytest.fixture
def mock_genai_client():
    """Mock Gemini API client"""
    with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client_class:
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def service_config():
    """Create a test service configuration"""
    # Use a specific model for testing
    return GeminiEventServiceConfig(
        model="gemini-3-flash-preview",
        thinking_level="low",
        max_output_tokens=2048,
        max_attempts=3,
        initial_backoff_s=0.1,  # Short backoff for tests
    )


@pytest.fixture
def gemini_service(service_config, mock_genai_client):
    """Create a GeminiEventService instance with mocked client"""
    return GeminiEventService(cfg=service_config, api_key="test-api-key")


@pytest.fixture
def sample_game_state():
    """Sample game state for testing"""
    return {
        "date": "1848-05-15",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "health": 100, "role": "leader"},
            {"name": "Mary", "health": 100, "role": "cook"},
        ],
        "resources": {
            "food": 500,
            "ammo": 100,
            "money": 200,
            "medicine": 50,
            "clothing": 75,
            "oxen": 4,
            "wagon_parts": 10,
        },
        "inventory": [{"item_id": "rifle", "quantity": 2}],
        "flags": [],
        "recent_log": ["Started the journey"],
    }


@pytest.fixture
def sample_event_draft():
    """Sample EventDraft for testing"""
    return EventDraft(
        schema_version=DraftSchemaVersion.V1,
        event_id="test-event-123",
        title="River Crossing",
        event_type=EventType.HAZARD,
        scene_text="You arrive at a rushing river. The water is deep and the current is strong.",
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
                label="Use the ferry",
                prompt="Pay to use the ferry service",
                risk=RiskLevel.LOW,
                requirements=[
                    Requirement(
                        requirement_type=RequirementType.RESOURCE_AT_LEAST,
                        ui_text="Requires $10",
                        resource=ResourceKey.MONEY,
                        min_value=10,
                    )
                ],
            ),
        ],
        safety_warnings=[],
        debug_tags=["water", "crossing"],
    )


# ------------------------------
# Configuration Tests
# ------------------------------


class TestGeminiEventServiceConfig:
    """Tests for GeminiEventServiceConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        # Note: The default model is evaluated at class definition time,
        # so we can't change it via environment variable after that.
        # Instead, we test that a config is created with expected defaults.
        config = GeminiEventServiceConfig()
        # Model should be set (either from env or default)
        assert config.model
        assert isinstance(config.model, str)
        assert config.thinking_level == "low"
        assert config.max_output_tokens == 2048
        assert config.max_attempts == 3
        assert config.initial_backoff_s == 0.6

    def test_custom_config(self):
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

    def test_config_validation_empty_model(self):
        """Test that empty model raises ValueError"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="")

    def test_config_validation_whitespace_model(self):
        """Test that whitespace-only model raises ValueError"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="   ")


# ------------------------------
# Initialization Tests
# ------------------------------


class TestGeminiEventServiceInitialization:
    """Tests for GeminiEventService initialization"""

    def test_init_with_api_key(self, service_config):
        """Test initialization with explicit API key"""
        with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client:
            service = GeminiEventService(cfg=service_config, api_key="my-api-key")
            mock_client.assert_called_once_with(api_key="my-api-key")
            assert service.cfg == service_config

    def test_init_without_api_key(self, service_config):
        """Test initialization without API key (uses environment)"""
        with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client:
            service = GeminiEventService(cfg=service_config, api_key=None)
            mock_client.assert_called_once_with()
            assert service.cfg == service_config

    def test_safety_settings_configured(self, gemini_service):
        """Test that safety settings are configured"""
        assert gemini_service.safety_settings is not None
        assert len(gemini_service.safety_settings) == 4


# ------------------------------
# generate_event_draft Tests
# ------------------------------


class TestGenerateEventDraft:
    """Tests for generate_event_draft method"""

    def test_successful_generation(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test successful event draft generation"""
        # Mock the API response
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        # Generate event
        result = gemini_service.generate_event_draft(sample_game_state)

        # Verify result
        assert isinstance(result, EventDraft)
        assert result.title == sample_event_draft.title
        assert result.event_type == sample_event_draft.event_type
        assert len(result.choices) == 2

        # Verify API was called correctly
        mock_genai_client.models.generate_content.assert_called_once()
        call_kwargs = mock_genai_client.models.generate_content.call_args

        # Check that prompt includes game state
        assert "Independence, Missouri" in call_kwargs[1]["contents"]

    def test_generates_uuid_for_event_id(
        self, gemini_service, mock_genai_client, sample_game_state
    ):
        """Test that a UUID is generated for event_id"""
        import uuid
        
        # We need to capture the generated UUID to return it in the mock response
        generated_uuid = None
        
        def generate_with_uuid(*args, **kwargs):
            nonlocal generated_uuid
            # Extract the UUID from the prompt
            prompt = kwargs.get("contents", "")
            # Find "event_id MUST be exactly: <uuid>"
            import re
            match = re.search(r'event_id MUST be exactly: ([a-f0-9-]+)', prompt)
            if match:
                generated_uuid = match.group(1)
                # Create a response with that UUID
                draft_dict = {
                    "schema_version": "event_draft.v1",
                    "event_id": generated_uuid,
                    "title": "Test Event",
                    "event_type": "hazard",
                    "scene_text": "A test event",
                    "choices": [
                        {
                            "choice_id": "A",
                            "label": "Continue",
                            "prompt": "Keep going",
                            "risk": "low",
                            "requirements": []
                        }
                    ],
                    "safety_warnings": [],
                    "debug_tags": []
                }
                mock_response = Mock()
                mock_response.text = json.dumps(draft_dict)
                return mock_response
        
        mock_genai_client.models.generate_content.side_effect = generate_with_uuid

        result = gemini_service.generate_event_draft(sample_game_state)

        # Event ID should be a valid UUID
        assert result.event_id
        assert len(result.event_id) == 36  # UUID format
        # Verify it's actually a valid UUID
        try:
            uuid.UUID(result.event_id)
        except ValueError:
            pytest.fail(f"event_id '{result.event_id}' is not a valid UUID")

    def test_includes_allowed_resources_in_prompt(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test that prompt includes allowed resources"""
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        gemini_service.generate_event_draft(sample_game_state)

        call_kwargs = mock_genai_client.models.generate_content.call_args
        prompt = call_kwargs[1]["contents"]

        # Check for allowed resources
        assert "food" in prompt
        assert "ammo" in prompt
        assert "money" in prompt


# ------------------------------
# resolve_event Tests
# ------------------------------


class TestResolveEvent:
    """Tests for resolve_event method"""

    def test_successful_resolution(
        self, gemini_service, mock_genai_client, sample_event_draft, sample_game_state
    ):
        """Test successful event resolution"""
        # Create expected resolution
        resolution = EventResolution(
            schema_version=ResolutionSchemaVersion.V1,
            event_id=sample_event_draft.event_id,
            choice_id="A",
            outcome_title="Successfully crossed",
            outcome_text="You manage to ford the river without incident.",
            effects=[
                Effect(
                    op=EffectOp.ADVANCE_DAYS,
                    note="River crossing took time",
                    days=1,
                )
            ],
        )

        # Mock the API response
        mock_response = Mock()
        mock_response.text = resolution.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        # Resolve event
        result = gemini_service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        # Verify result
        assert isinstance(result, EventResolution)
        assert result.event_id == sample_event_draft.event_id
        assert result.choice_id == "A"
        assert result.outcome_title == "Successfully crossed"

    def test_resolution_with_rng(
        self, gemini_service, mock_genai_client, sample_event_draft, sample_game_state
    ):
        """Test resolution with RNG data"""
        resolution = EventResolution(
            schema_version=ResolutionSchemaVersion.V1,
            event_id=sample_event_draft.event_id,
            choice_id="A",
            outcome_title="Partial success",
            outcome_text="You crossed but lost some supplies.",
            effects=[],
        )

        mock_response = Mock()
        mock_response.text = resolution.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        # Provide RNG data
        rng_data = {"roll": 75, "threshold": 50}
        result = gemini_service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
            rng=rng_data,
        )

        # Verify RNG data is included in prompt
        call_kwargs = mock_genai_client.models.generate_content.call_args
        prompt = call_kwargs[1]["contents"]
        assert "75" in prompt  # RNG roll value should be in prompt

    def test_resolution_includes_draft_context(
        self, gemini_service, mock_genai_client, sample_event_draft, sample_game_state
    ):
        """Test that resolution prompt includes draft context"""
        resolution = EventResolution(
            schema_version=ResolutionSchemaVersion.V1,
            event_id=sample_event_draft.event_id,
            choice_id="A",
            outcome_title="Test",
            outcome_text="Test outcome",
            effects=[],
        )

        mock_response = Mock()
        mock_response.text = resolution.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        gemini_service.resolve_event(
            draft=sample_event_draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        call_kwargs = mock_genai_client.models.generate_content.call_args
        prompt = call_kwargs[1]["contents"]

        # Verify draft details are in prompt
        assert sample_event_draft.title in prompt
        assert sample_event_draft.event_id in prompt


# ------------------------------
# Validation Tests
# ------------------------------


class TestValidation:
    """Tests for validation logic"""

    def test_validation_with_valid_json(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test that valid JSON passes validation"""
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        result = gemini_service.generate_event_draft(sample_game_state)
        assert isinstance(result, EventDraft)

    def test_validation_with_invalid_json_triggers_repair(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test that invalid JSON triggers repair"""
        # First call returns invalid JSON
        invalid_json = '{"event_id": "test", "invalid_field": true}'

        # Second call (repair) returns valid JSON
        mock_response_1 = Mock()
        mock_response_1.text = invalid_json

        mock_response_2 = Mock()
        mock_response_2.text = sample_event_draft.model_dump_json()

        mock_genai_client.models.generate_content.side_effect = [
            mock_response_1,
            mock_response_2,
        ]

        result = gemini_service.generate_event_draft(sample_game_state)

        # Should have called API twice (original + repair)
        assert mock_genai_client.models.generate_content.call_count == 2
        assert isinstance(result, EventDraft)


# ------------------------------
# repair_json Tests
# ------------------------------


class TestRepairJson:
    """Tests for repair_json method"""

    def test_repair_json_success(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test successful JSON repair"""
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        bad_json = '{"event_id": "test"}'
        error_msg = "Missing required field: title"

        result = gemini_service._repair_json(
            schema_model=EventDraft,
            raw_text=bad_json,
            error=error_msg,
        )

        assert isinstance(result, EventDraft)

        # Verify repair prompt includes error and bad JSON
        call_kwargs = mock_genai_client.models.generate_content.call_args
        prompt = call_kwargs[1]["contents"]
        assert error_msg in prompt
        assert bad_json in prompt

    def test_repair_json_empty_response_raises_error(
        self, gemini_service, mock_genai_client
    ):
        """Test that empty repair response raises error"""
        mock_response = Mock()
        mock_response.text = ""
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(
            GeminiEventServiceError, match="Repair call returned empty response"
        ):
            gemini_service._repair_json(
                schema_model=EventDraft,
                raw_text='{"bad": "json"}',
                error="Validation failed",
            )


# ------------------------------
# Error Handling Tests
# ------------------------------


class TestErrorHandling:
    """Tests for error handling scenarios"""

    def test_empty_response_raises_error(
        self, gemini_service, mock_genai_client, sample_game_state
    ):
        """Test that empty response raises error"""
        mock_response = Mock()
        mock_response.text = ""
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Empty response text"):
            gemini_service.generate_event_draft(sample_game_state)

    def test_none_response_raises_error(
        self, gemini_service, mock_genai_client, sample_game_state
    ):
        """Test that None response raises error"""
        mock_response = Mock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(GeminiEventServiceError, match="Empty response text"):
            gemini_service.generate_event_draft(sample_game_state)

    def test_retry_on_api_error(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test retry logic on API errors"""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()

        mock_genai_client.models.generate_content.side_effect = [
            Exception("API Error"),
            mock_response,
        ]

        result = gemini_service.generate_event_draft(sample_game_state)

        # Should have retried and succeeded
        assert mock_genai_client.models.generate_content.call_count == 2
        assert isinstance(result, EventDraft)

    def test_max_retries_exceeded(
        self, mock_genai_client, sample_game_state
    ):
        """Test that max retries raises error"""
        # Configure service with only 2 attempts for faster test
        config = GeminiEventServiceConfig(
            model="test-model",
            max_attempts=2,
            initial_backoff_s=0.01,
        )
        service = GeminiEventService(cfg=config, api_key="test-key")

        # All calls fail
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")

        with pytest.raises(
            GeminiEventServiceError, match="failed after 2 attempts"
        ):
            service.generate_event_draft(sample_game_state)

        # Should have attempted exactly max_attempts times
        assert mock_genai_client.models.generate_content.call_count == 2

    def test_backoff_increases_on_retry(
        self, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test that backoff time increases on retries"""
        import time

        config = GeminiEventServiceConfig(
            model="test-model",
            max_attempts=3,
            initial_backoff_s=0.05,
        )
        service = GeminiEventService(cfg=config, api_key="test-key")

        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()

        # Fail twice, then succeed
        mock_genai_client.models.generate_content.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            mock_response,
        ]

        start = time.time()
        result = service.generate_event_draft(sample_game_state)
        elapsed = time.time() - start

        # Should have waited at least initial_backoff + (initial_backoff * 1.8)
        # 0.05 + 0.09 = 0.14 seconds minimum
        assert elapsed >= 0.14
        assert isinstance(result, EventDraft)


# ------------------------------
# Safety Settings Tests
# ------------------------------


class TestSafetySettings:
    """Tests for safety settings"""

    def test_safety_settings_present(self, gemini_service):
        """Test that safety settings are configured"""
        settings = gemini_service.safety_settings
        assert len(settings) == 4

    def test_safety_settings_block_hate_speech(self, gemini_service):
        """Test hate speech is blocked at low threshold"""
        from google.genai import types

        hate_setting = next(
            (
                s
                for s in gemini_service.safety_settings
                if s.category == types.HarmCategory.HARM_CATEGORY_HATE_SPEECH
            ),
            None,
        )
        assert hate_setting is not None
        assert (
            hate_setting.threshold
            == types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        )

    def test_safety_settings_block_sexual_content(self, gemini_service):
        """Test sexual content is blocked at low threshold"""
        from google.genai import types

        sexual_setting = next(
            (
                s
                for s in gemini_service.safety_settings
                if s.category
                == types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT
            ),
            None,
        )
        assert sexual_setting is not None
        assert (
            sexual_setting.threshold
            == types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        )


# ------------------------------
# Integration-style Tests
# ------------------------------


class TestIntegration:
    """Integration-style tests for complete workflows"""

    def test_full_event_workflow(
        self, gemini_service, mock_genai_client, sample_game_state, sample_event_draft
    ):
        """Test full workflow: generate draft -> resolve event"""
        # Mock draft generation
        mock_draft_response = Mock()
        mock_draft_response.text = sample_event_draft.model_dump_json()

        # Mock resolution
        resolution = EventResolution(
            schema_version=ResolutionSchemaVersion.V1,
            event_id=sample_event_draft.event_id,
            choice_id="A",
            outcome_title="Success",
            outcome_text="You made it across!",
            effects=[],
        )
        mock_resolution_response = Mock()
        mock_resolution_response.text = resolution.model_dump_json()

        mock_genai_client.models.generate_content.side_effect = [
            mock_draft_response,
            mock_resolution_response,
        ]

        # Generate draft
        draft = gemini_service.generate_event_draft(sample_game_state)
        assert isinstance(draft, EventDraft)

        # Resolve with player choice
        result = gemini_service.resolve_event(
            draft=draft,
            choice_id="A",
            game_state=sample_game_state,
        )

        assert isinstance(result, EventResolution)
        assert result.event_id == draft.event_id
        assert result.choice_id == "A"

    def test_close_method(self, gemini_service):
        """Test close method can be called"""
        # Should not raise an error
        gemini_service.close()


# ------------------------------
# Edge Cases
# ------------------------------


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_minimal_game_state(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test with minimal game state"""
        minimal_state: Dict[str, Any] = {}

        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        result = gemini_service.generate_event_draft(minimal_state)
        assert isinstance(result, EventDraft)

    def test_large_game_state(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test with large game state"""
        large_state = {
            "date": "1848-05-15",
            "location": "Independence, Missouri",
            "miles_traveled": 500,
            "season": "summer",
            "party": [{"name": f"Person{i}", "health": 100} for i in range(10)],
            "resources": {
                "food": 10000,
                "ammo": 5000,
                "money": 9999,
                "medicine": 500,
                "clothing": 500,
                "oxen": 10,
                "wagon_parts": 100,
            },
            "inventory": [{"item_id": f"item{i}", "quantity": 10} for i in range(20)],
            "flags": [f"flag{i}" for i in range(50)],
            "recent_log": [f"Event {i}" for i in range(100)],
        }

        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        result = gemini_service.generate_event_draft(large_state)
        assert isinstance(result, EventDraft)

        # Verify recent_log was truncated to last 6 entries
        call_kwargs = mock_genai_client.models.generate_content.call_args
        prompt = call_kwargs[1]["contents"]
        # Should only include last 6 log entries
        assert "Event 99" in prompt
        assert "Event 94" in prompt
        assert "Event 93" not in prompt  # Earlier entries should be excluded

    def test_special_characters_in_game_state(
        self, gemini_service, mock_genai_client, sample_event_draft
    ):
        """Test handling of special characters in game state"""
        special_state = {
            "location": "Fort O'Brien & Co.",
            "party": [{"name": "José María", "health": 100}],
            "recent_log": ['Event with "quotes" and special chars: <>&'],
        }

        mock_response = Mock()
        mock_response.text = sample_event_draft.model_dump_json()
        mock_genai_client.models.generate_content.return_value = mock_response

        result = gemini_service.generate_event_draft(special_state)
        assert isinstance(result, EventDraft)
