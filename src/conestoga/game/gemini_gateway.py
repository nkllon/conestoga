"""
Gemini 3 Integration - LLM gateway with fallback behavior
Implements Requirements 5.1-5.6, 9.1-9.5, 16.1-16.4, 17.1

REQUIREMENT: All Gemini API calls MUST use Gemini 3 models.
Preview APIs (gemini-3-flash-preview, gemini-3-pro-preview) are acceptable.
"""

import json
import os

from dotenv import load_dotenv

from .events import (
    Choice,
    Effect,
    EffectType,
    EventDraft,
    EventResolution,
    FallbackDeck,
    Outcome,
)
from .state import GameState, ItemCatalog
from .validators import validate_effect_targets

# Load environment variables
load_dotenv()

try:
    from google import genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiGateway:
    """Gateway to Gemini API with validation and fallback"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.fallback_deck = FallbackDeck()
        self.max_retries = 2
        self.enabled = self.api_key is not None and GEMINI_AVAILABLE
        self.resource_exhausted = False  # Track if quota is exhausted
        self.client = None
        self.model_name = "gemini-3-flash-preview"
        self.last_event_source: str = "unknown"
        self.last_resolution_source: str = "unknown"
        self.last_failure_reason: str | None = None

        if not GEMINI_AVAILABLE:
            print("Warning: google-genai not available. Running in fallback mode.")
        elif not self.enabled:
            print("Warning: No Gemini API key found. Running in fallback mode.")
        else:
            try:
                # REQUIREMENT: Use Gemini 3 models exclusively (preview APIs acceptable)
                # Using gemini-3-flash-preview for fast event generation (Req 16.1)
                self.client = genai.Client(api_key=self.api_key)
                print("[Gemini] Connected to Gemini 3 API successfully")
            except Exception as e:
                print(f"[Gemini] Failed to initialize: {e}")
                self.enabled = False

    def generate_event_draft(
        self, game_state: GameState, item_catalog: ItemCatalog, tier: str = "minor"
    ) -> EventDraft:
        """Generate event draft from Gemini or fallback"""
        self.last_failure_reason = None
        if not self.is_online():
            print("[Gemini] API disabled or offline, using fallback deck")
            self.last_event_source = "fallback"
            self.last_failure_reason = (
                "offline" if not self.enabled else "resource_exhausted"
            )
            return self.fallback_deck.get_random_event(game_state)

        try:
            # Build prompt with game state context (Req 3.3, 15.1)
            prompt = self._build_event_prompt(game_state, tier)

            print(f"[Gemini] Generating {tier} event...")
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            # Parse and validate response (Req 5.2)
            event = self._parse_event_draft(response.text, item_catalog)
            if event:
                print(f"[Gemini] Generated event: {event.event_id}")
                self.last_event_source = "gemini"
                return event
            else:
                print("[Gemini] Validation failed, using fallback")
                self.last_event_source = "fallback"
                self.last_failure_reason = "validation_error"
                return self.fallback_deck.get_random_event(game_state)

        except Exception as e:
            print(f"[Gemini] Error generating event: {e}")
            self.last_failure_reason = str(e)
            # Check if quota exhausted and disable API
            self._check_resource_exhausted(e)
            self.last_event_source = "fallback"
            # Fallback on API errors (Req 9.3, 9.5)
            return self.fallback_deck.get_random_event(game_state)

    def generate_event_resolution(
        self,
        event_draft: EventDraft,
        choice_id: str,
        game_state: GameState,
        item_catalog: ItemCatalog,
    ) -> EventResolution | None:
        """Generate event resolution from Gemini or fallback"""
        self.last_failure_reason = None
        if not self.is_online():
            print("[Gemini] API disabled or offline, using fallback resolutions")
            self.last_resolution_source = "fallback"
            self.last_failure_reason = (
                "offline" if not self.enabled else "resource_exhausted"
            )
            return self.fallback_deck.get_resolution(event_draft.event_id, choice_id)

        try:
            # Build resolution prompt
            prompt = self._build_resolution_prompt(event_draft, choice_id, game_state)

            print(f"[Gemini] Resolving choice {choice_id}...")
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            # Parse and validate response
            resolution = self._parse_event_resolution(response.text, choice_id, item_catalog)
            if resolution:
                print(f"[Gemini] Generated resolution for {choice_id}")
                self.last_resolution_source = "gemini"
                return resolution
            else:
                print("[Gemini] Validation failed, using fallback")
                self.last_resolution_source = "fallback"
                self.last_failure_reason = "validation_error"
                return self.fallback_deck.get_resolution(event_draft.event_id, choice_id)

        except Exception as e:
            print(f"[Gemini] Error generating resolution: {e}")
            self.last_failure_reason = str(e)
            # Check if quota exhausted and disable API
            self._check_resource_exhausted(e)
            self.last_resolution_source = "fallback"
            return self.fallback_deck.get_resolution(event_draft.event_id, choice_id)

    def _build_event_prompt(self, game_state: GameState, tier: str) -> str:
        """Build prompt for event generation (Req 3.3, 15.1)

        Uses Gemini 3 API for state-aware event generation.
        """
        state_summary = f"""You are generating an Oregon Trail-style event for a westward journey simulation.

GAME STATE:
- Day: {game_state.day}
- Miles traveled: {game_state.miles_traveled} / {game_state.target_miles}
- Party size: {len(game_state.party)} members
- Resources: Food={game_state.food}, Money=${game_state.money}, Water={game_state.water},
  Ammo={game_state.ammo}
- Inventory: {", ".join(game_state.inventory.keys()) if game_state.inventory else "empty"}

Generate a {tier} event that:
1. Creates a narrative challenge appropriate for the Oregon Trail (1840s)
2. Offers 2-3 meaningful choices
3. Uses ONLY these effect types: adjust_resource, add_item, remove_item, adjust_health,
   adjust_morale
4. References only existing inventory items or common trail items
5. Is historically grounded (no anachronisms)

Return ONLY a valid JSON object with this exact structure:
{{
  "event_id": "unique_event_id",
  "title": "Brief event title",
  "narrative": "Event description (2-3 sentences)",
  "choices": [
    {{
      "id": "choice_1",
      "text": "Brief choice text describing the action",
      "prerequisites": []
    }}
  ],
  "tier": "{tier}"
}}

IMPORTANT: Return ONLY the JSON object, no markdown formatting, no explanation."""
        return state_summary

    def _build_resolution_prompt(
        self, event: EventDraft, choice_id: str, game_state: GameState
    ) -> str:
        """Build prompt for resolution generation (Req 5.6)"""
        choice = next((c for c in event.choices if c.id == choice_id), None)
        if not choice:
            raise ValueError(f"Choice {choice_id} not found")

        prompt = f"""Generate the outcome for a player's choice in an Oregon Trail event.

EVENT: {event.narrative}
PLAYER CHOSE: {choice.text}

CURRENT STATE:
- Food: {game_state.food}, Money: ${game_state.money}, Water: {game_state.water},
  Ammo: {game_state.ammo}
- Inventory: {", ".join(game_state.inventory.keys()) if game_state.inventory else "empty"}

Generate a resolution with:
1. Narrative outcome (2-3 sentences)
2. Concrete effects using ONLY these operations: add_item, remove_item, modify_resource,
   modify_stat, set_flag
3. Resource names: food, water, money, ammo, wagon_health
4. Reasonable values (±1-20 for resources, existing items only)

Return ONLY valid JSON:
{{
  "text": "What happened as a result (2-3 sentences)",
  "effects": [
    {{"operation": "modify_resource", "target": "food", "value": -5}},
    {{"operation": "modify_resource", "target": "money", "value": 10}}
  ]
}}

IMPORTANT: Return ONLY the JSON object."""
        return prompt

    def _parse_event_draft(
        self, response_text: str, item_catalog: ItemCatalog
    ) -> EventDraft | None:
        """Parse and validate event draft from Gemini response (Req 5.2)"""
        try:
            # Clean response (remove markdown formatting if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Extract JSON from markdown code block
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
                if cleaned.startswith("json"):
                    cleaned = "\n".join(cleaned.split("\n")[1:])

            data = json.loads(cleaned)

            # Validate required fields
            if not all(k in data for k in ["event_id", "title", "narrative", "choices"]):
                print("[Gemini] Missing required fields in event draft")
                return None

            # Parse choices
            choices = []
            for c_data in data["choices"]:
                # Parse prerequisites
                prereqs = []
                for p_data in c_data.get("prerequisites", []):
                    if isinstance(p_data, dict):
                        from .events import Prerequisite

                        prereqs.append(
                            Prerequisite(
                                type=p_data.get("type", ""),
                                target=p_data.get("target"),
                                value=p_data.get("value"),
                            )
                        )

                choice = Choice(
                    id=c_data.get("id", ""), text=c_data.get("text", ""), prerequisites=prereqs
                )
                choices.append(choice)

            event = EventDraft(
                event_id=data["event_id"],
                title=data.get("title", "Event"),
                narrative=data["narrative"],
                choices=choices,
                tier=data.get("tier", "minor"),
            )

            # Validate event (Req 5.2)
            errors = event.validate(item_catalog)
            if errors:
                print(f"[Gemini] Validation errors: {errors}")
                return None

            return event

        except json.JSONDecodeError as e:
            print(f"[Gemini] JSON parse error: {e}")
            print(f"[Gemini] Response was: {response_text[:200]}...")
            return None
        except Exception as e:
            print(f"[Gemini] Parse error: {e}")
            return None

    def _parse_event_resolution(
        self, response_text: str, choice_id: str, item_catalog: ItemCatalog
    ) -> EventResolution | None:
        """Parse and validate event resolution (Req 5.2, 8.1)"""
        try:
            # Clean response
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
                if cleaned.startswith("json"):
                    cleaned = "\n".join(cleaned.split("\n")[1:])

            data = json.loads(cleaned)

            # Validate required fields
            if not all(k in data for k in ["text", "effects"]):
                print("[Gemini] Missing required fields in resolution")
                return None

            # Parse effects with whitelist validation (Req 8.1, 8.2)
            effects = []
            effect_errors: list[str] = []
            for e_data in data["effects"]:
                try:
                    effect_type = EffectType[e_data["operation"].upper()]
                    effect = Effect(
                        operation=effect_type,
                        target=e_data.get("target"),
                        value=e_data.get("value"),
                    )
                    effects.append(effect)
                except (KeyError, ValueError):
                    print(f"[Gemini] Invalid effect operation: {e_data.get('operation')}")
                    effect_errors.append(f"Invalid effect operation: {e_data.get('operation')}")

            if effect_errors:
                print("[Gemini] Effect validation errors, discarding resolution.")
                return None

            validation_errors = validate_effect_targets(effects, item_catalog)
            if validation_errors:
                print(f"[Gemini] Effect validation errors: {validation_errors}")
                return None

            outcome = Outcome(text=data["text"], effects=effects)

            resolution = EventResolution(choice_id=choice_id, outcome=outcome)

            return resolution

        except json.JSONDecodeError as e:
            print(f"[Gemini] JSON parse error in resolution: {e}")
            return None
        except Exception as e:
            print(f"[Gemini] Parse error in resolution: {e}")
            return None

    def is_online(self) -> bool:
        return self.enabled and not self.resource_exhausted

    def _check_resource_exhausted(self, error: Exception) -> bool:
        """Check if error is RESOURCE_EXHAUSTED and disable API if so"""
        error_str = str(error)
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str or "quota" in error_str.lower():
            print(
                "[Gemini] RESOURCE_EXHAUSTED detected - API quota exceeded. Disabling Gemini API."
            )
            self.resource_exhausted = True
            return True
        return False


class ValidationEngine:
    """Validate events and effects"""

    @staticmethod
    def validate_event_draft(event: EventDraft, item_catalog: ItemCatalog) -> list[str]:
        return event.validate(item_catalog)

    @staticmethod
    def validate_effects(effects: list) -> bool:
        return True
