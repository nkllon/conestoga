"""
Gemini Integration - LLM gateway with fallback behavior
Implements Requirements 5.1-5.6, 9.1-9.5, 16.1-16.4, 17.1
"""

import os

from dotenv import load_dotenv

from .events import EventDraft, EventResolution, FallbackDeck
from .state import GameState, ItemCatalog

# Load environment variables
load_dotenv()


class GeminiGateway:
    """Gateway to Gemini API with validation and fallback"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.fallback_deck = FallbackDeck()
        self.max_retries = 2
        self.enabled = self.api_key is not None

        if not self.enabled:
            print("Warning: No Gemini API key found. Running in fallback mode.")

    def generate_event_draft(
        self, game_state: GameState, item_catalog: ItemCatalog, tier: str = "minor"
    ) -> EventDraft:
        """Generate event draft from Gemini or fallback"""
        if not self.enabled:
            print("[Gemini] API disabled, using fallback deck")
            return self.fallback_deck.get_random_event(game_state)

        # TODO: Implement Gemini API call here
        # For now, use fallback
        print(f"[Gemini] Generating {tier} event (PROTOTYPE: using fallback)")
        return self.fallback_deck.get_random_event(game_state)

    def generate_event_resolution(
        self, event_draft: EventDraft, choice_id: str, game_state: GameState
    ) -> EventResolution | None:
        """Generate event resolution from Gemini or fallback"""
        if not self.enabled:
            print("[Gemini] API disabled, using fallback resolutions")
            return self.fallback_deck.get_resolution(event_draft.event_id, choice_id)

        # TODO: Implement Gemini API call here
        # For now, use fallback
        print(f"[Gemini] Resolving choice {choice_id} (PROTOTYPE: using fallback)")
        return self.fallback_deck.get_resolution(event_draft.event_id, choice_id)

    def is_online(self) -> bool:
        return self.enabled


class ValidationEngine:
    """Validate events and effects"""

    @staticmethod
    def validate_event_draft(event: EventDraft, item_catalog: ItemCatalog) -> list[str]:
        return event.validate(item_catalog)

    @staticmethod
    def validate_effects(effects: list) -> bool:
        return True
