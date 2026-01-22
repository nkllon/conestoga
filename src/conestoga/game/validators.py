"""
Validation utilities for Conestoga game content.
Enforces choice counts, uniqueness, and effect targeting against the catalog.
"""

from __future__ import annotations

from collections.abc import Iterable

from .events import Effect, EffectType, EventDraft
from .state import ItemCatalog

ALLOWED_RESOURCES = {"food", "water", "money", "ammo", "wagon_health"}


def validate_choices(event: EventDraft) -> list[str]:
    """Validate event choices for count, uniqueness, and text."""
    errors: list[str] = []
    choices = event.choices
    if len(choices) < 2 or len(choices) > 3:
        errors.append("Choices must be between 2 and 3 options")

    seen_ids: set[str] = set()
    for c in choices:
        if not c.id:
            errors.append("Choice id is required")
        if c.id in seen_ids:
            errors.append(f"Duplicate choice id: {c.id}")
        seen_ids.add(c.id)
        if not c.text or not c.text.strip():
            errors.append(f"Choice text missing for id {c.id or '<unknown>'}")
    return errors


def validate_effects(effects: Iterable[Effect], item_catalog: ItemCatalog) -> list[str]:
    """Validate effects against allowed operations, resources, and catalog items."""
    errors: list[str] = []
    for eff in effects:
        op = eff.operation
        if op in {EffectType.ADD_ITEM, EffectType.REMOVE_ITEM}:
            if not eff.target or not item_catalog.has_item(eff.target):
                errors.append(f"Unknown item_id in effect: {eff.target}")
            if eff.value is not None and not isinstance(eff.value, (int, float)):
                errors.append(f"Item quantity must be numeric for {eff.target}")
        elif op == EffectType.MODIFY_RESOURCE:
            if eff.target not in ALLOWED_RESOURCES:
                errors.append(f"Invalid resource target: {eff.target}")
            if eff.value is None or not isinstance(eff.value, (int, float)):
                errors.append(f"Resource delta must be numeric for {eff.target}")
        elif op in {EffectType.DAMAGE_WAGON, EffectType.REPAIR_WAGON}:
            if eff.value is not None and eff.value < 0:
                errors.append("Wagon health delta must be non-negative")
        elif op in {EffectType.SET_FLAG, EffectType.CLEAR_FLAG}:
            if not eff.target:
                errors.append("Flag effects require a target name")
        elif op == EffectType.LOG_JOURNAL:
            if eff.target is None or not str(eff.target).strip():
                errors.append("LOG_JOURNAL requires text content")
        elif op == EffectType.ADVANCE_TIME:
            # No-op for now; keep for potential expansion.
            if eff.value is not None and not isinstance(eff.value, (int, float)):
                errors.append("ADVANCE_TIME expects integer days")
        elif op == EffectType.QUEUE_FOLLOWUP:
            # Placeholder for future follow-up events; ensure identifier present.
            if not eff.target:
                errors.append("QUEUE_FOLLOWUP requires target identifier")
    return errors


def validate_effect_targets(
    effects: Iterable[Effect] | None, item_catalog: ItemCatalog
) -> list[str]:
    """Wrapper to handle None effects collections safely."""
    if not effects:
        return []
    return validate_effects(effects, item_catalog)
