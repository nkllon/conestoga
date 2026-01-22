"""Tests for GeminiEventService"""
from unittest.mock import MagicMock, Mock, patch
import json
import pytest
from pydantic import ValidationError

from conestoga.services.gemini_event_service import (
    GeminiEventService,
    GeminiEventServiceConfig,
    GeminiEventServiceError,
    SYSTEM_INSTRUCTION,
    ALLOWED_RESOURCE_KEYS,
    ALLOWED_ITEM_IDS,
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
def mock_genai_client():
    """Mock the google.genai.Client"""
    with patch("conestoga.services.gemini_event_service.genai.Client") as mock_client:
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
def game_state():
    """Sample game state for testing"""
    return {
        "date": "1848-04-01",
        "location": "Independence, Missouri",
        "miles_traveled": 0,
        "season": "spring",
        "party": [
            {"name": "John", "health": 100, "role": "leader"},
            {"name": "Mary", "health": 100, "role": "hunter"},
        ],
        "resources": {
            "food": 200,
            "ammo": 50,
            "money": 300,
            "medicine": 10,
            "clothing": 20,
            "oxen": 4,
            "wagon_parts": 5,
        },
        "inventory": [{"item_id": "rifle", "quantity": 2}],
        "flags": ["started_journey"],
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
        scene_text="You've reached a wide river. The water looks deep and swift.",
        choices=[
            EventChoice(
                choice_id="A",
                label="Ford the river",
                prompt="Try to cross directly",
                risk=RiskLevel.HIGH,
                requirements=[],
            ),
            EventChoice(
                choice_id="B",
                label="Wait for ferry",
                prompt="Wait for the ferry (costs $5)",
                risk=RiskLevel.LOW,
                requirements=[],
            ),
        ],
        safety_warnings=[],
        debug_tags=["river", "crossing"],
    )


class TestGeminiEventServiceConfig:
    """Tests for GeminiEventServiceConfig"""

    def test_default_config(self):
        """Test config with defaults"""
        config = GeminiEventServiceConfig()
        assert config.model is not None
        assert config.thinking_level == "low"
        assert config.max_output_tokens == 2048
        assert config.max_attempts == 3
        assert config.initial_backoff_s == 0.6

    def test_config_validation_empty_model(self):
        """Test that empty model raises ValueError"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="")

    def test_config_validation_whitespace_model(self):
        """Test that whitespace-only model raises ValueError"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            GeminiEventServiceConfig(model="   ")

    def test_config_custom_values(self):
        """Test config with custom values"""
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


class TestGeminiEventServiceInit:
    """Tests for GeminiEventService initialization"""

    def test_init_with_api_key(self, service_config, mock_genai_client):
        """Test initialization with API key"""
        service = GeminiEventService(service_config, api_key="test-key")
        mock_genai_client.assert_called_once_with(api_key="test-key")
        assert service.cfg == service_config

    def test_init_without_api_key(self, service_config, mock_genai_client):
        """Test initialization without API key (uses env)"""
        service = GeminiEventService(service_config)
        mock_genai_client.assert_called_once_with()
        assert service.cfg == service_config

    def test_safety_settings(self, service_config, mock_genai_client):
        """Test that safety settings are configured"""
        service = GeminiEventService(service_config)
        assert len(service.safety_settings) == 4

    def test_close(self, service_config, mock_genai_client):
        """Test close method"""
        service = GeminiEventService(service_config)
        service.close()  # Should not raise


class TestGenerateEventDraft:
    """Tests for generate_event_draft method"""

    def test_generate_event_draft_success(self, service_config, mock_genai_client, game_state):
        """Test successful event draft generation"""
        # Setup mock response
        mock_response = Mock()
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            result = service.generate_event_draft(game_state)

        assert isinstance(result, EventDraft)
        assert result.event_id == "test-uuid"
        assert len(result.choices) >= 1

    def test_generate_event_draft_includes_game_state(
        self, service_config, mock_genai_client, game_state
    ):
        """Test that game state is included in the prompt"""
        mock_response = Mock()
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            service.generate_event_draft(game_state)

        # Verify the prompt contains game state
        call_args = mock_client_instance.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "Independence, Missouri" in prompt
        assert "1848-04-01" in prompt


class TestResolveEvent:
    """Tests for resolve_event method"""

    def test_resolve_event_success(
        self, service_config, mock_genai_client, game_state, sample_event_draft
    ):
        """Test successful event resolution"""
        mock_response = Mock()
        valid_resolution = EventResolution(
            schema_version=ResolutionSchemaVersion.V1,
            event_id=sample_event_draft.event_id,
            choice_id="A",
            outcome_title="Success",
            outcome_text="You successfully crossed the river.",
            effects=[
                Effect(
                    op=EffectOp.DELTA_RESOURCE,
                    note="Lost some food",
                    resource=ResourceKey.FOOD,
                    delta=-10,
                )
            ],
        )
        mock_response.text = valid_resolution.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        result = service.resolve_event(sample_event_draft, "A", game_state)

        assert isinstance(result, EventResolution)
        assert result.event_id == sample_event_draft.event_id
        assert result.choice_id == "A"

    def test_resolve_event_with_rng(
        self, service_config, mock_genai_client, game_state, sample_event_draft
    ):
        """Test event resolution with RNG inputs"""
        mock_response = Mock()
        valid_resolution = EventResolution(
            schema_version=ResolutionSchemaVersion.V1,
            event_id=sample_event_draft.event_id,
            choice_id="B",
            outcome_title="Waited",
            outcome_text="You waited for the ferry.",
            effects=[],
        )
        mock_response.text = valid_resolution.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        rng_data = {"roll": 0.75, "outcome": "success"}
        result = service.resolve_event(sample_event_draft, "B", game_state, rng=rng_data)

        assert isinstance(result, EventResolution)
        
        # Verify RNG was included in prompt
        call_args = mock_client_instance.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "0.75" in prompt


class TestValidationAndRepair:
    """Tests for validation and repair logic"""

    def test_repair_json_on_validation_error(self, service_config, mock_genai_client, game_state):
        """Test that repair_json is called on validation error"""
        # First call returns invalid JSON
        mock_response_invalid = Mock()
        mock_response_invalid.text = '{"event_id": "test", "invalid": "data"}'

        # Repair call returns valid JSON
        mock_response_valid = Mock()
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response_valid.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = [
            mock_response_invalid,
            mock_response_valid,
        ]
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            result = service.generate_event_draft(game_state)

        # Should have called generate_content twice (initial + repair)
        assert mock_client_instance.models.generate_content.call_count == 2
        assert isinstance(result, EventDraft)

    def test_repair_json_includes_error_details(self, service_config, mock_genai_client, game_state):
        """Test that repair call includes validation error details"""
        # First call returns invalid JSON
        mock_response_invalid = Mock()
        mock_response_invalid.text = '{"event_id": "test"}'

        # Repair call returns valid JSON
        mock_response_valid = Mock()
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response_valid.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = [
            mock_response_invalid,
            mock_response_valid,
        ]
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            result = service.generate_event_draft(game_state)

        # Check that repair call included error context
        second_call_args = mock_client_instance.models.generate_content.call_args_list[1]
        repair_prompt = second_call_args[1]["contents"]
        assert "validation" in repair_prompt.lower() or "error" in repair_prompt.lower()


class TestErrorHandling:
    """Tests for error handling scenarios"""

    def test_empty_response_raises_error(self, service_config, mock_genai_client, game_state):
        """Test that empty response raises GeminiEventServiceError"""
        mock_response = Mock()
        mock_response.text = ""

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            with pytest.raises(GeminiEventServiceError, match="Empty response"):
                service.generate_event_draft(game_state)

    def test_none_response_raises_error(self, service_config, mock_genai_client, game_state):
        """Test that None response raises GeminiEventServiceError"""
        mock_response = Mock()
        mock_response.text = None

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            with pytest.raises(GeminiEventServiceError, match="Empty response"):
                service.generate_event_draft(game_state)

    def test_retry_on_api_error(self, service_config, mock_genai_client, game_state):
        """Test retry logic on API error"""
        # First two calls fail, third succeeds
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        
        mock_response_valid = Mock()
        mock_response_valid.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            mock_response_valid,
        ]
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            with patch("time.sleep"):  # Skip actual sleep in test
                result = service.generate_event_draft(game_state)

        assert mock_client_instance.models.generate_content.call_count == 3
        assert isinstance(result, EventDraft)

    def test_max_attempts_exceeded(self, service_config, mock_genai_client, game_state):
        """Test that error is raised after max attempts"""
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = Exception("API Error")
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            with patch("time.sleep"):  # Skip actual sleep in test
                with pytest.raises(GeminiEventServiceError, match="failed after 3 attempts"):
                    service.generate_event_draft(game_state)

        assert mock_client_instance.models.generate_content.call_count == 3

    def test_repair_empty_response_raises_error(self, service_config, mock_genai_client, game_state):
        """Test that empty response from repair raises error after retries"""
        # First call returns invalid JSON, repair returns empty - this pattern repeats for all attempts
        mock_response_invalid = Mock()
        mock_response_invalid.text = '{"event_id": "test"}'

        mock_response_empty = Mock()
        mock_response_empty.text = ""

        mock_client_instance = MagicMock()
        # Each attempt: invalid response, then empty repair response
        mock_client_instance.models.generate_content.side_effect = [
            mock_response_invalid,
            mock_response_empty,
            mock_response_invalid,
            mock_response_empty,
            mock_response_invalid,
            mock_response_empty,
        ]
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            with patch("time.sleep"):  # Skip actual sleep in test
                with pytest.raises(GeminiEventServiceError, match="failed after 3 attempts"):
                    service.generate_event_draft(game_state)


class TestPromptBuilding:
    """Tests for prompt building methods"""

    def test_draft_prompt_includes_constraints(self, service_config, mock_genai_client, game_state):
        """Test that draft prompt includes all necessary constraints"""
        service = GeminiEventService(service_config, api_key="test")
        event_id = "test-event-123"
        
        prompt = service._build_draft_prompt(event_id, game_state)
        
        assert event_id in prompt
        assert "2-4" in prompt  # Choice count requirement
        assert str(ALLOWED_RESOURCE_KEYS) in prompt or "food" in prompt
        assert "Independence, Missouri" in prompt

    def test_draft_prompt_limits_recent_log(self, service_config, mock_genai_client):
        """Test that draft prompt limits recent_log to last 6 entries"""
        service = GeminiEventService(service_config, api_key="test")
        
        game_state = {
            "date": "1848-04-01",
            "location": "Independence",
            "miles_traveled": 0,
            "season": "spring",
            "party": [],
            "resources": {},
            "inventory": [],
            "flags": [],
            "recent_log": [f"Log entry {i}" for i in range(20)],  # 20 entries
        }
        
        prompt = service._build_draft_prompt("test-id", game_state)
        
        # Should only include last 6
        assert "Log entry 19" in prompt
        assert "Log entry 14" in prompt
        assert "Log entry 13" not in prompt

    def test_resolution_prompt_includes_all_context(
        self, service_config, mock_genai_client, game_state, sample_event_draft
    ):
        """Test that resolution prompt includes draft, choice, and RNG"""
        service = GeminiEventService(service_config, api_key="test")
        
        rng_data = {"roll": 0.5, "success": True}
        prompt = service._build_resolution_prompt(
            event_id=sample_event_draft.event_id,
            choice_id="A",
            draft=sample_event_draft,
            game_state=game_state,
            rng=rng_data,
        )
        
        assert sample_event_draft.event_id in prompt
        assert "A" in prompt
        assert "River Crossing" in prompt
        assert "0.5" in prompt
        assert str(ALLOWED_RESOURCE_KEYS) in prompt or "food" in prompt


class TestSafetySettings:
    """Tests for safety settings configuration"""

    def test_default_safety_settings_count(self, service_config, mock_genai_client):
        """Test that all safety categories are configured"""
        service = GeminiEventService(service_config, api_key="test")
        assert len(service.safety_settings) == 4

    def test_safety_settings_applied_to_calls(
        self, service_config, mock_genai_client, game_state
    ):
        """Test that safety settings are applied to API calls"""
        mock_response = Mock()
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            service.generate_event_draft(game_state)

        call_args = mock_client_instance.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config.safety_settings is not None


class TestSystemInstruction:
    """Tests for system instruction usage"""

    def test_system_instruction_applied(self, service_config, mock_genai_client, game_state):
        """Test that system instruction is applied to API calls"""
        mock_response = Mock()
        valid_draft = EventDraft(
            schema_version=DraftSchemaVersion.V1,
            event_id="test-uuid",
            title="Test Event",
            event_type=EventType.HAZARD,
            scene_text="A test scene",
            choices=[
                EventChoice(
                    choice_id="A",
                    label="Option A",
                    prompt="Choose A",
                    risk=RiskLevel.LOW,
                    requirements=[],
                )
            ],
            safety_warnings=[],
            debug_tags=[],
        )
        mock_response.text = valid_draft.model_dump_json()

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        service = GeminiEventService(service_config)
        
        with patch("uuid.uuid4", return_value="test-uuid"):
            service.generate_event_draft(game_state)

        call_args = mock_client_instance.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config.system_instruction == SYSTEM_INSTRUCTION

    def test_system_instruction_content(self):
        """Test that system instruction contains key safety rules"""
        assert "valid JSON" in SYSTEM_INSTRUCTION
        assert "PG-13" in SYSTEM_INSTRUCTION
        assert "Oregon Trail" in SYSTEM_INSTRUCTION
