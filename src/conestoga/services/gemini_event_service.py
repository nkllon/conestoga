# services/gemini_event_service.py
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

# Updated import for conestoga package structure
from conestoga.models.events import EventDraft, EventResolution


T = TypeVar("T", bound=BaseModel)


# ------------------------------
# Guardrails & prompt templates
# ------------------------------

SYSTEM_INSTRUCTION = """You are a narrative event generator for an Oregon Trail-inspired game.

Hard rules:
- Output must be valid JSON that matches the provided response schema. Do not output markdown.
- Keep text PG-13. No sexual content. No hate or slurs. No harassment. No extremist content.
- Avoid medical advice or diagnosis. You may describe mild sickness as fiction, but do not give real-world medical instructions.
- Avoid violence targeted at protected groups. If Indigenous people appear, portray them respectfully and avoid stereotypes.
- Do not instruct the user to do anything in the real world; this is an in-game narrative only.
- Keep event scenes concise and interactive.
"""

# IMPORTANT: SDK docs warn not to duplicate the schema in your prompt (no example JSON).
# So we DO NOT paste the schema or example objects into the prompt.

ALLOWED_RESOURCE_KEYS = ["food", "ammo", "money", "medicine", "clothing", "oxen", "wagon_parts"]

# Keep this list short and real for demo; expand later from your item catalog.
ALLOWED_ITEM_IDS = [
    "shovel",
    "rope",
    "spare_wheel",
    "rifle",
    "ammo_box",
    "flour_sack",
    "medicine_kit",
    "warm_blanket",
    "fishing_hook",
    "wagon_axle",
]


def _json_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ------------------------------
# Service config + return types
# ------------------------------

@dataclass(frozen=True)
class GeminiEventServiceConfig:
    model: str = "gemini-3-flash-preview"  # Gemini API docs show this model id
    thinking_level: str = "low"            # "minimal/low/medium/high" depending on model
    max_output_tokens: int = 2048
    # retry logic
    max_attempts: int = 3
    initial_backoff_s: float = 0.6


class GeminiEventServiceError(RuntimeError):
    pass


class GeminiEventService:
    """
    Minimal, robust integration point:
      - structured outputs (JSON + schema)
      - strict validation
      - repair loop
      - safety settings
      - thinking level control
    """

    def __init__(self, cfg: GeminiEventServiceConfig, api_key: Optional[str] = None):
        self.cfg = cfg

        # The SDK can also auto-pick up GEMINI_API_KEY or GOOGLE_API_KEY from env.
        # If both are set, GOOGLE_API_KEY takes precedence.
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()

        self.safety_settings = self._default_safety_settings()

    def close(self) -> None:
        # Good hygiene: close underlying HTTP connections if your app exits.
        # self.client.close() # google-genai client doesn't explicitly require close, but good practice if available
        pass 

    # ------------------------------
    # Public API
    # ------------------------------

    def generate_event_draft(self, game_state: Dict[str, Any]) -> EventDraft:
        event_id = str(uuid.uuid4())
        prompt = self._build_draft_prompt(event_id=event_id, game_state=game_state)
        return self._call_structured(EventDraft, prompt)

    def resolve_event(
        self,
        draft: EventDraft,
        choice_id: str,
        game_state: Dict[str, Any],
        rng: Optional[Dict[str, Any]] = None,
    ) -> EventResolution:
        prompt = self._build_resolution_prompt(
            event_id=draft.event_id,
            choice_id=choice_id,
            draft=draft,
            game_state=game_state,
            rng=rng or {"note": "no_rng"},
        )
        return self._call_structured(EventResolution, prompt)

    # ------------------------------
    # Prompt builders
    # ------------------------------

    def _build_draft_prompt(self, event_id: str, game_state: Dict[str, Any]) -> str:
        """
        Provide only the state the model needs; keep it compact to reduce latency/cost.
        """
        state_payload = {
            "date": game_state.get("date"),
            "location": game_state.get("location"),
            "miles_traveled": game_state.get("miles_traveled"),
            "season": game_state.get("season"),
            "party": game_state.get("party"),
            "resources": game_state.get("resources"),
            "inventory": game_state.get("inventory"),
            "flags": game_state.get("flags", []),
            "recent_log": game_state.get("recent_log", [])[-6:],
        }

        return f"""
Generate a new interactive trail event for an Oregon Trail-inspired game.

Event constraints:
- event_id MUST be exactly: {event_id}
- choices MUST be 2-4.
- Each choice must be plausible given the state and era.
- Requirements must be checkable by the engine.
- Effects should be SMALL and plausible (no huge deltas).

Allowed resource keys (for effects/requirements): {_json_compact(ALLOWED_RESOURCE_KEYS)}
Allowed item_ids (for effects/requirements): {_json_compact(ALLOWED_ITEM_IDS)}

Game state (JSON):
{_json_compact(state_payload)}
""".strip()

    def _build_resolution_prompt(
        self,
        event_id: str,
        choice_id: str,
        draft: EventDraft,
        game_state: Dict[str, Any],
        rng: Dict[str, Any],
    ) -> str:
        """
        The resolution prompt includes the draft + player choice, and can incorporate RNG we compute locally.
        """
        # Keep the embedded draft small (avoid dumping the full schema or huge text)
        draft_payload = {
            "event_id": draft.event_id,
            "title": draft.title,
            "event_type": draft.event_type,
            "scene_text": draft.scene_text,
            "choices": [{"choice_id": c.choice_id, "label": c.label, "prompt": c.prompt} for c in draft.choices],
        }

        state_payload = {
            "date": game_state.get("date"),
            "location": game_state.get("location"),
            "miles_traveled": game_state.get("miles_traveled"),
            "party": game_state.get("party"),
            "resources": game_state.get("resources"),
            "inventory": game_state.get("inventory"),
            "flags": game_state.get("flags", []),
        }

        return f"""
Resolve the outcome of the player's choice in the event.

Hard constraints:
- event_id MUST be exactly: {event_id}
- choice_id MUST be exactly: {choice_id}
- Effects must be small, plausible, and consistent with the choice.
- Do not include medical advice, slurs, or explicit content.

Allowed resource keys: {_json_compact(ALLOWED_RESOURCE_KEYS)}
Allowed item_ids: {_json_compact(ALLOWED_ITEM_IDS)}

Draft (JSON):
{_json_compact(draft_payload)}

Current game state (JSON):
{_json_compact(state_payload)}

RNG inputs (JSON) - treat as authoritative:
{_json_compact(rng)}
""".strip()

    # ------------------------------
    # Core call + validation + repair
    # ------------------------------

    def _call_structured(self, schema_model: Type[T], prompt: str) -> T:
        """
        Calls Gemini with structured outputs and validates into the target Pydantic model.
        Includes backoff + repair loops.
        """
        last_err: Optional[Exception] = None
        backoff = self.cfg.initial_backoff_s

        for attempt in range(1, self.cfg.max_attempts + 1):
            try:
                resp = self.client.models.generate_content(
                    model=self.cfg.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        max_output_tokens=self.cfg.max_output_tokens,

                        # Thinking control (Gemini 3):
                        thinking_config=types.ThinkingConfig(thinking_level=self.cfg.thinking_level),

                        # Safety settings:
                        safety_settings=self.safety_settings,

                        # Structured output:
                        response_mime_type="application/json",
                        response_schema=schema_model,
                    ),
                )

                # If safety blocked, response.text can be empty.
                raw_text = (resp.text or "").strip()
                if not raw_text:
                    raise GeminiEventServiceError("Empty response text (possibly safety-blocked).")

                try:
                    return schema_model.model_validate_json(raw_text)
                except ValidationError as ve:
                    # Repair once per attempt
                    repaired = self._repair_json(schema_model, raw_text=raw_text, error=str(ve))
                    return repaired

            except Exception as e:
                last_err = e
                if attempt < self.cfg.max_attempts:
                    time.sleep(backoff)
                    backoff *= 1.8
                    continue
                break

        raise GeminiEventServiceError(f"Gemini call failed after {self.cfg.max_attempts} attempts: {last_err}")

    def _repair_json(self, schema_model: Type[T], raw_text: str, error: str) -> T:
        """
        Second-pass “fix JSON to match schema” call.
        Uses the same response_schema to force compliance.
        """
        repair_prompt = f"""
The previous response was supposed to be valid JSON matching the provided response schema,
but it failed validation.

Validation error:
{error}

Bad JSON:
{raw_text}

Return ONLY corrected JSON that matches the schema. Do not add commentary.
""".strip()

        resp = self.client.models.generate_content(
            model=self.cfg.model,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=self.cfg.max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_level=self.cfg.thinking_level),
                safety_settings=self.safety_settings,
                response_mime_type="application/json",
                response_schema=schema_model,
            ),
        )

        raw_text_2 = (resp.text or "").strip()
        if not raw_text_2:
            raise GeminiEventServiceError("Repair call returned empty response.")

        return schema_model.model_validate_json(raw_text_2)

    # ------------------------------
    # Safety settings tuned for this game
    # ------------------------------

    def _default_safety_settings(self) -> List[types.SafetySetting]:
        """
        Hackathon-safe defaults: block low+ for hate/sexual; be moderate on harassment/danger.
        Adjust after playtesting so you don't accidentally block normal frontier narrative.
        """
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ]
