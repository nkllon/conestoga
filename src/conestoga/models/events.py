# models/events.py
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Enumerations (tight, predictable) ----------

class EventType(str, Enum):
    HAZARD = "hazard"
    TRADE = "trade"
    DISCOVERY = "discovery"
    SOCIAL = "social"
    WEATHER = "weather"
    LANDMARK = "landmark"
    MISHAP = "mishap"
    ANIMAL = "animal"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResourceKey(str, Enum):
    FOOD = "food"
    AMMO = "ammo"
    MONEY = "money"
    MEDICINE = "medicine"
    CLOTHING = "clothing"
    OXEN = "oxen"
    WAGON_PARTS = "wagon_parts"


class StatKey(str, Enum):
    HEALTH = "health"     # overall party health
    MORALE = "morale"     # overall party morale


class RequirementType(str, Enum):
    HAS_ITEM = "has_item"
    RESOURCE_AT_LEAST = "resource_at_least"
    STAT_AT_LEAST = "stat_at_least"
    FLAG_SET = "flag_set"


class EffectOp(str, Enum):
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    DELTA_RESOURCE = "delta_resource"
    DELTA_STAT = "delta_stat"
    SET_FLAG = "set_flag"
    CLEAR_FLAG = "clear_flag"
    ADVANCE_DAYS = "advance_days"


class DraftSchemaVersion(str, Enum):
    V1 = "event_draft.v1"


class ResolutionSchemaVersion(str, Enum):
    V1 = "event_resolution.v1"


# ---------- Atomic building blocks ----------

class Requirement(BaseModel):
    """
    A machine-checkable requirement that determines whether a choice is selectable.

    All fields are PRESENT, but some are allowed to be null depending on requirement_type.
    This keeps the JSON shape stable and avoids optional-missing-key issues.
    """
    model_config = ConfigDict(extra="forbid")

    requirement_type: RequirementType = Field(description="Type of requirement.")
    ui_text: str = Field(description="Short UI text explaining the requirement.")

    # Only one of these should be non-null depending on requirement_type:
    item_id: Optional[str] = Field(description="Required if requirement_type=has_item else null.", default=None)
    resource: Optional[ResourceKey] = Field(description="Required if requirement_type=resource_at_least else null.", default=None)
    stat: Optional[StatKey] = Field(description="Required if requirement_type=stat_at_least else null.", default=None)
    flag: Optional[str] = Field(description="Required if requirement_type=flag_set else null.", default=None)

    # Numeric thresholds:
    min_value: Optional[int] = Field(description="Required for *_at_least requirement types, else null.", default=None)
    quantity: Optional[int] = Field(description="Required if requirement_type=has_item else null.", default=None)


class Effect(BaseModel):
    """
    A deterministic, engine-applied change to game state.

    The engine MUST validate + clamp values (never trust model deltas blindly).
    """
    model_config = ConfigDict(extra="forbid")

    op: EffectOp = Field(description="Operation to apply.")
    note: str = Field(description="Human-readable reason; safe to show in logs.")

    # Targets (only some used depending on op):
    item_id: Optional[str] = Field(description="Item ID for add/remove item ops, else null.", default=None)
    quantity: Optional[int] = Field(description="Item quantity for add/remove item ops, else null.", default=None)

    resource: Optional[ResourceKey] = Field(description="Resource key for delta_resource ops, else null.", default=None)
    stat: Optional[StatKey] = Field(description="Stat key for delta_stat ops, else null.", default=None)
    delta: Optional[int] = Field(description="Signed integer delta for stat/resource ops, else null.", default=None)

    flag: Optional[str] = Field(description="Flag name for set/clear flag ops, else null.", default=None)
    days: Optional[int] = Field(description="Days to advance for advance_days op, else null.", default=None)


class EventChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice_id: str = Field(description="Stable ID used to resolve the choice (e.g., 'A', 'B', 'C').")
    label: str = Field(description="Short choice label, fits on one line.")
    prompt: str = Field(description="What the player is choosing to do (1-2 sentences).")

    risk: RiskLevel = Field(description="Approximate risk for the player.")
    requirements: List[Requirement] = Field(description="Requirements to select this choice; empty list allowed.")


# ---------- Top-level payloads ----------

class EventDraft(BaseModel):
    """
    Model output for the *draft* of an encounter.
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: DraftSchemaVersion = Field(description="Schema version for compatibility.")
    event_id: str = Field(description="Event UUID provided by the game; must be echoed back.")
    title: str = Field(description="Short event title.")
    event_type: EventType = Field(description="High-level category.")
    scene_text: str = Field(description="Narrative scene text shown to player (keep under ~800 chars).")

    choices: List[EventChoice] = Field(description="2-4 choices. Always include at least 2 choices.")

    # Safety / UI affordances:
    safety_warnings: List[str] = Field(description="Optional content warnings; can be empty.")
    debug_tags: List[str] = Field(description="Short tags for debugging/telemetry; can be empty.")


class EventResolution(BaseModel):
    """
    Model output for the *resolution* after a player picks a choice.
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: ResolutionSchemaVersion = Field(description="Schema version for compatibility.")
    event_id: str = Field(description="Must match the draft's event_id.")
    choice_id: str = Field(description="Must match one of the draft choice_id values.")

    outcome_title: str = Field(description="Short outcome title.")
    outcome_text: str = Field(description="Narrative of what happened (keep under ~900 chars).")
    effects: List[Effect] = Field(description="Engine-applied effects; empty list allowed.")
