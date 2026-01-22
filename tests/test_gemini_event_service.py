"""Tests for GeminiEventService"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from conestoga.models.events import (
    DraftSchemaVersion,
    Effect,
    EffectOp,
    EventChoice,
    EventDraft,
    EventResolution,
    EventType,
    ResolutionSchemaVersion,
    RiskLevel,
)
from conestoga.services.gemini_event_service import (
    GeminiEventService,
    GeminiEventServiceConfig,
    GeminiEventServiceError,
)

# -------------------- Fixtures --------------------


@pytest.fixture
def mock_genai_client():
    """Mock the genai.Client"""
    with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client:
        yield mock_client


@pytest.fixture
def service_config():
    """Create a test configuration"""
    return GeminiEventServiceConfig(
        model="gemini-3-flash-preview",
        thinking_level="low",
        max_output_tokens=2048,
        max_attempts=3,
        initial_backoff_s=0.1,  # Faster for tests
    )


@pytest.fixture
def service(mock_genai_client, service_config):
    """Create a GeminiEventService instance with mocked client"""
    return GeminiEventService(cfg=service_config, api_key="test-api-key")


@pytest.fixture
def sample_game_state() -> dict[str, Any]:
    """Sample game state for testing"""
    return {
        "date": "1848-05-01",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "health": 100, "role": "leader"},
            {"name": "Mary", "health": 100, "role": "navigator"},
        ],
        "resources": {
            "food": 500,
            "ammo": 50,
            "money": 200,
            "medicine": 10,
            "clothing": 20,
            "oxen": 4,
            "wagon_parts": 3,
        },
        "inventory": ["shovel", "rope"],
        "flags": ["well_rested"],
        "recent_log": ["Started journey", "Bought supplies"],
    }


@pytest.fixture
def sample_event_draft() -> EventDraft:
    """Sample EventDraft for testing"""
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
                prompt="Wade across carefully with the wagon.",
                risk=RiskLevel.HIGH,
                requirements=[],
            ),
            EventChoice(
                choice_id="B",
                label="Wait for calmer waters",
                prompt="Set up camp and wait a few days.",
                risk=RiskLevel.LOW,
                requirements=[],
            ),
        ],
        safety_warnings=[],
        debug_tags=["river", "hazard"],
    )


# -------------------- Config Tests --------------------


def test_config_validation_valid():
    """Test that valid config passes validation"""
    config = GeminiEventServiceConfig(model="gemini-3-flash-preview")
    assert config.model == "gemini-3-flash-preview"
    assert config.thinking_level == "low"


def test_config_validation_empty_model():
    """Test that empty model string raises ValueError"""
    with pytest.raises(ValueError, match="must be a non-empty string"):
        GeminiEventServiceConfig(model="")


def test_config_validation_whitespace_model():
    """Test that whitespace-only model raises ValueError"""
    with pytest.raises(ValueError, match="must be a non-empty string"):
        GeminiEventServiceConfig(model="   ")


def test_config_model_default():
    """Test that config has a sensible default model"""
    config = GeminiEventServiceConfig()
    # The default is evaluated at class definition time, so it will use
    # whatever GEMINI_MODEL_ID was set to when the module was loaded
    assert config.model is not None
    assert len(config.model) > 0


def test_config_can_override_model():
    """Test that config model can be explicitly overridden"""
    config = GeminiEventServiceConfig(model="custom-model")
    assert config.model == "custom-model"


# -------------------- Service Initialization Tests --------------------


def test_service_initialization_with_api_key(mock_genai_client, service_config):
    """Test service initializes correctly with API key"""
    service = GeminiEventService(cfg=service_config, api_key="test-key")
    mock_genai_client.assert_called_once_with(api_key="test-key")
    assert service.cfg == service_config
    assert service.safety_settings is not None


def test_service_initialization_without_api_key(mock_genai_client, service_config):
    """Test service initializes correctly without explicit API key"""
    service = GeminiEventService(cfg=service_config, api_key=None)
    mock_genai_client.assert_called_once_with()
    assert service.cfg == service_config


def test_service_close(service):
    """Test service close method"""
    # Should not raise an error
    service.close()


# -------------------- Safety Settings Tests --------------------


def test_default_safety_settings(service):
    """Test that safety settings are properly configured"""
    safety_settings = service._default_safety_settings()
    assert len(safety_settings) == 4
    # Verify all required harm categories are covered
    categories = [s.category for s in safety_settings]
    from google.genai import types

    assert types.HarmCategory.HARM_CATEGORY_HATE_SPEECH in categories
    assert types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in categories
    assert types.HarmCategory.HARM_CATEGORY_HARASSMENT in categories
    assert types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in categories


# -------------------- generate_event_draft Tests --------------------


def test_generate_event_draft_success(service, sample_game_state, sample_event_draft):
    """Test successful event draft generation"""
    # Mock the response
    mock_response = Mock()
    mock_response.text = sample_event_draft.model_dump_json()

    service.client.models.generate_content = Mock(return_value=mock_response)

    result = service.generate_event_draft(sample_game_state)

    assert isinstance(result, EventDraft)
    assert result.title == "River Crossing"
    assert result.event_type == EventType.HAZARD
    assert len(result.choices) == 2


def test_generate_event_draft_creates_uuid(service, sample_game_state):
    """Test that generate_event_draft creates a UUID for event_id"""
    import uuid

    # Create a proper event draft with a valid UUID
    valid_uuid = str(uuid.uuid4())
    event_draft_with_uuid = EventDraft(
        schema_version=DraftSchemaVersion.V1,
        event_id=valid_uuid,
        title="Test Event",
        event_type=EventType.HAZARD,
        scene_text="Test scene",
        choices=[
            EventChoice(
                choice_id="A",
                label="Choice A",
                prompt="Test prompt",
                risk=RiskLevel.LOW,
                requirements=[],
            )
        ],
        safety_warnings=[],
        debug_tags=[],
    )

    mock_response = Mock()
    mock_response.text = event_draft_with_uuid.model_dump_json()
    service.client.models.generate_content = Mock(return_value=mock_response)

    result = service.generate_event_draft(sample_game_state)

    # Verify UUID format - should not raise ValueError
    try:
        uuid.UUID(result.event_id)
    except ValueError:
        pytest.fail("event_id is not a valid UUID")


def test_generate_event_draft_builds_correct_prompt(
    service, sample_game_state, sample_event_draft
):
    """Test that generate_event_draft builds prompt with correct game state"""
    mock_response = Mock()
    mock_response.text = sample_event_draft.model_dump_json()
    service.client.models.generate_content = Mock(return_value=mock_response)

    service.generate_event_draft(sample_game_state)

    # Verify generate_content was called
    call_args = service.client.models.generate_content.call_args
    prompt = call_args[1]["contents"]

    # Check that key game state elements are in the prompt
    assert "Independence, Missouri" in prompt
    assert "1848-05-01" in prompt
    assert "food" in prompt


# -------------------- resolve_event Tests --------------------


def test_resolve_event_success(service, sample_event_draft, sample_game_state):
    """Test successful event resolution"""
    # Create a sample resolution
    resolution = EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id="test-event-123",
        choice_id="A",
        outcome_title="Safe Crossing",
        outcome_text="You successfully ford the river.",
        effects=[
            Effect(
                op=EffectOp.DELTA_RESOURCE,
                note="Some supplies got wet",
                resource="food",
                delta=-10,
            )
        ],
    )

    mock_response = Mock()
    mock_response.text = resolution.model_dump_json()
    service.client.models.generate_content = Mock(return_value=mock_response)

    result = service.resolve_event(
        draft=sample_event_draft,
        choice_id="A",
        game_state=sample_game_state,
        rng={"roll": 75},
    )

    assert isinstance(result, EventResolution)
    assert result.event_id == "test-event-123"
    assert result.choice_id == "A"
    assert len(result.effects) == 1


def test_resolve_event_builds_correct_prompt(
    service, sample_event_draft, sample_game_state
):
    """Test that resolve_event builds prompt correctly"""
    resolution = EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id="test-event-123",
        choice_id="A",
        outcome_title="Success",
        outcome_text="You made it.",
        effects=[],
    )

    mock_response = Mock()
    mock_response.text = resolution.model_dump_json()
    service.client.models.generate_content = Mock(return_value=mock_response)

    service.resolve_event(
        draft=sample_event_draft,
        choice_id="A",
        game_state=sample_game_state,
        rng={"roll": 50},
    )

    call_args = service.client.models.generate_content.call_args
    prompt = call_args[1]["contents"]

    # Verify the prompt contains expected elements
    assert "test-event-123" in prompt
    assert "A" in prompt
    assert '"roll":50' in prompt or '"roll": 50' in prompt


def test_resolve_event_with_default_rng(service, sample_event_draft, sample_game_state):
    """Test resolve_event with no RNG provided"""
    resolution = EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id="test-event-123",
        choice_id="A",
        outcome_title="Success",
        outcome_text="Done.",
        effects=[],
    )

    mock_response = Mock()
    mock_response.text = resolution.model_dump_json()
    service.client.models.generate_content = Mock(return_value=mock_response)

    result = service.resolve_event(
        draft=sample_event_draft, choice_id="A", game_state=sample_game_state, rng=None
    )

    assert isinstance(result, EventResolution)


# -------------------- Validation & Error Handling Tests --------------------


def test_call_structured_empty_response(service, sample_game_state):
    """Test handling of empty response (safety blocked)"""
    mock_response = Mock()
    mock_response.text = ""
    service.client.models.generate_content = Mock(return_value=mock_response)

    with pytest.raises(GeminiEventServiceError, match="Empty response text"):
        service.generate_event_draft(sample_game_state)


def test_call_structured_validation_error_triggers_repair(
    service, sample_game_state, sample_event_draft
):
    """Test that validation errors trigger repair logic"""
    # First response is invalid JSON
    bad_response = Mock()
    bad_response.text = '{"invalid": "json without required fields"}'

    # Second response (repair) is valid
    good_response = Mock()
    good_response.text = sample_event_draft.model_dump_json()

    service.client.models.generate_content = Mock(
        side_effect=[bad_response, good_response]
    )

    result = service.generate_event_draft(sample_game_state)

    # Should have called generate_content twice (original + repair)
    assert service.client.models.generate_content.call_count == 2
    assert isinstance(result, EventDraft)


def test_repair_json_success(service, sample_event_draft):
    """Test successful JSON repair"""
    bad_json = '{"invalid": "data"}'
    error_msg = "Missing required field: event_id"

    # Mock the repair call
    mock_response = Mock()
    mock_response.text = sample_event_draft.model_dump_json()
    service.client.models.generate_content = Mock(return_value=mock_response)

    result = service._repair_json(EventDraft, raw_text=bad_json, error=error_msg)

    assert isinstance(result, EventDraft)
    # Verify the repair prompt was used
    call_args = service.client.models.generate_content.call_args
    prompt = call_args[1]["contents"]
    assert "validation" in prompt.lower() or "error" in prompt.lower()


def test_repair_json_empty_response(service):
    """Test repair_json with empty response"""
    mock_response = Mock()
    mock_response.text = ""
    service.client.models.generate_content = Mock(return_value=mock_response)

    with pytest.raises(GeminiEventServiceError, match="Repair call returned empty"):
        service._repair_json(EventDraft, raw_text="bad", error="error")


# -------------------- Retry Logic Tests --------------------


def test_retry_logic_with_backoff(service, sample_game_state, sample_event_draft):
    """Test that service retries with exponential backoff on failure"""
    # Mock failures followed by success
    mock_response = Mock()
    mock_response.text = sample_event_draft.model_dump_json()

    service.client.models.generate_content = Mock(
        side_effect=[
            Exception("Temporary failure"),
            Exception("Another failure"),
            mock_response,
        ]
    )

    with patch("time.sleep") as mock_sleep:
        result = service.generate_event_draft(sample_game_state)

        # Should have retried and eventually succeeded
        assert service.client.models.generate_content.call_count == 3
        assert isinstance(result, EventDraft)

        # Verify backoff was applied
        assert mock_sleep.call_count == 2
        # Check backoff increases (0.1 * 1.8 = 0.18)
        assert mock_sleep.call_args_list[0][0][0] == pytest.approx(0.1)
        assert mock_sleep.call_args_list[1][0][0] == pytest.approx(0.18)


def test_max_attempts_exceeded(service, sample_game_state):
    """Test that service fails after max attempts"""
    service.client.models.generate_content = Mock(
        side_effect=Exception("Persistent failure")
    )

    with patch("time.sleep"):
        with pytest.raises(
            GeminiEventServiceError, match="failed after 3 attempts"
        ):
            service.generate_event_draft(sample_game_state)

        # Should have tried max_attempts times
        assert service.client.models.generate_content.call_count == 3


# -------------------- Prompt Building Tests --------------------


def test_build_draft_prompt_structure(service):
    """Test the structure of draft prompts"""
    game_state = {
        "date": "1848-05-01",
        "location": "Independence",
        "miles_traveled": 100,
        "season": "spring",
        "party": [],
        "resources": {"food": 100},
        "inventory": [],
        "flags": [],
        "recent_log": ["event1", "event2"],
    }

    prompt = service._build_draft_prompt(event_id="test-123", game_state=game_state)

    # Verify key elements are present
    assert "test-123" in prompt
    assert "1848-05-01" in prompt
    assert "Independence" in prompt
    assert "food" in prompt
    assert "2-4" in prompt  # choice requirement


def test_build_draft_prompt_truncates_log(service, sample_game_state):
    """Test that draft prompt only includes last 6 log entries"""
    game_state = sample_game_state.copy()
    game_state["recent_log"] = [f"event_{i}" for i in range(20)]

    prompt = service._build_draft_prompt(event_id="test", game_state=game_state)

    # Should only include last 6
    assert "event_19" in prompt
    assert "event_14" in prompt
    assert "event_13" not in prompt


def test_build_resolution_prompt_structure(service, sample_event_draft, sample_game_state):
    """Test the structure of resolution prompts"""
    prompt = service._build_resolution_prompt(
        event_id="test-123",
        choice_id="A",
        draft=sample_event_draft,
        game_state=sample_game_state,
        rng={"roll": 50},
    )

    # Verify key elements
    assert "test-123" in prompt
    assert "A" in prompt
    assert "River Crossing" in prompt
    assert '"roll":50' in prompt or '"roll": 50' in prompt


# -------------------- Integration-like Tests --------------------


def test_full_event_flow(service, sample_game_state, sample_event_draft):
    """Test a complete event generation and resolution flow"""
    # Mock draft generation
    draft_response = Mock()
    draft_response.text = sample_event_draft.model_dump_json()

    # Mock resolution
    resolution = EventResolution(
        schema_version=ResolutionSchemaVersion.V1,
        event_id=sample_event_draft.event_id,
        choice_id="A",
        outcome_title="Success",
        outcome_text="You made it across!",
        effects=[],
    )
    resolution_response = Mock()
    resolution_response.text = resolution.model_dump_json()

    service.client.models.generate_content = Mock(
        side_effect=[draft_response, resolution_response]
    )

    # Generate draft
    draft = service.generate_event_draft(sample_game_state)
    assert isinstance(draft, EventDraft)

    # Resolve choice
    result = service.resolve_event(
        draft=draft, choice_id="A", game_state=sample_game_state
    )
    assert isinstance(result, EventResolution)
    assert result.event_id == draft.event_id


def test_allowed_resource_keys_validation(service):
    """Test that service uses correct allowed resource keys"""
    from conestoga.services.gemini_event_service import ALLOWED_RESOURCE_KEYS

    expected_keys = ["food", "ammo", "money", "medicine", "clothing", "oxen", "wagon_parts"]
    assert set(ALLOWED_RESOURCE_KEYS) == set(expected_keys)


def test_allowed_item_ids_validation(service):
    """Test that service uses correct allowed item IDs"""
    from conestoga.services.gemini_event_service import ALLOWED_ITEM_IDS

    # Verify some expected items are in the list
    assert "shovel" in ALLOWED_ITEM_IDS
    assert "rope" in ALLOWED_ITEM_IDS
    assert "rifle" in ALLOWED_ITEM_IDS
    assert "medicine_kit" in ALLOWED_ITEM_IDS
