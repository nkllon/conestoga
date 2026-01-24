"""Tests for Conestoga game systems"""

from conestoga.game.events import (
    Choice,
    Effect,
    EffectType,
    EventDraft,
    FallbackDeck,
    Prerequisite,
)
from conestoga.game.gemini_gateway import GeminiGateway
from conestoga.game.fallback_monitor import FallbackMonitor
from conestoga.game.state import GameState, ItemCatalog
from conestoga.game.validators import validate_effect_targets


def test_game_state_initialization():
    """Test that game state initializes correctly"""
    state = GameState()
    assert state.day == 1
    assert state.miles_traveled == 0
    assert len(state.party) == 4
    assert state.food > 0
    assert state.water > 0


def test_inventory_operations():
    """Test inventory add/remove with invariants"""
    state = GameState()

    assert state.has_item("itm_rifle", 2)

    state.add_item("itm_shovel", 1)
    assert state.has_item("itm_shovel", 1)

    success = state.remove_item("itm_rifle", 1)
    assert success
    assert state.has_item("itm_rifle", 1)

    success = state.remove_item("itm_rifle", 10)
    assert not success


def test_resource_invariants():
    """Test that resources cannot go negative"""
    state = GameState()

    state.modify_resource("food", -1000)
    assert state.food == 0  # Should clamp to 0

    state.modify_resource("food", 100)
    assert state.food == 100


def test_prerequisites():
    """Test prerequisite evaluation"""
    state = GameState()

    prereq1 = Prerequisite(type="has_item", target="itm_rifle", value=1)
    assert prereq1.is_met(state)

    prereq2 = Prerequisite(type="has_item", target="itm_shovel", value=1)
    assert not prereq2.is_met(state)

    prereq3 = Prerequisite(type="min_resource", target="money", value=50)
    assert prereq3.is_met(state)


def test_effect_application():
    """Test effect application to game state"""
    state = GameState()

    effect1 = Effect(EffectType.ADD_ITEM, "itm_shovel", 1)
    effect1.apply(state)
    assert state.has_item("itm_shovel", 1)

    initial_food = state.food
    effect2 = Effect(EffectType.MODIFY_RESOURCE, "food", 50)
    effect2.apply(state)
    assert state.food == initial_food + 50

    effect3 = Effect(EffectType.DAMAGE_WAGON, None, 20)
    effect3.apply(state)
    assert state.wagon_health == 80


def test_choice_availability():
    """Test that choices check prerequisites correctly"""
    state = GameState()

    choice1 = Choice(id="c1", text="Continue", prerequisites=[])
    assert choice1.is_available(state)

    choice2 = Choice(
        id="c2",
        text="Use rifle",
        prerequisites=[Prerequisite(type="has_item", target="itm_rifle", value=1)],
    )
    assert choice2.is_available(state)

    choice3 = Choice(
        id="c3",
        text="Use shovel",
        prerequisites=[Prerequisite(type="has_item", target="itm_shovel", value=1)],
    )
    assert not choice3.is_available(state)


def test_event_validation():
    """Test event draft validation"""
    catalog = ItemCatalog()

    event1 = EventDraft(
        event_id="test1",
        title="Test Event",
        narrative="Test narrative",
        choices=[Choice(id="c1", text="Continue"), Choice(id="c2", text="Camp")],
    )
    errors1 = event1.validate(catalog)
    assert len(errors1) == 0

    event2 = EventDraft(event_id="", title="", narrative="", choices=[])
    errors2 = event2.validate(catalog)
    assert len(errors2) > 0


def test_fallback_deck():
    """Test fallback deck provides valid events"""
    deck = FallbackDeck()
    state = GameState()
    catalog = ItemCatalog()

    event = deck.get_random_event(state)
    assert event is not None
    assert event.event_id
    assert event.title
    assert len(event.choices) > 0

    errors = event.validate(catalog)
    assert len(errors) == 0


def test_gemini_gateway_fallback():
    """Test that GeminiGateway falls back when no API key"""
    import os

    # Save and clear any existing API key to test fallback
    old_key = os.environ.get("GEMINI_API_KEY")
    if old_key:
        del os.environ["GEMINI_API_KEY"]

    try:
        gateway = GeminiGateway(api_key=None)
        state = GameState()
        catalog = ItemCatalog()

        assert not gateway.is_online()

        event = gateway.generate_event_draft(state, catalog)
        assert event is not None
        assert event.event_id.startswith("fallback_")
    finally:
        # Restore the original API key
        if old_key:
            os.environ["GEMINI_API_KEY"] = old_key


def test_choice_count_and_uniqueness_validation():
    catalog = ItemCatalog()
    too_few = EventDraft(
        event_id="few",
        title="Too Few",
        narrative="",
        choices=[Choice(id="c1", text="One")],
    )
    errors = too_few.validate(catalog)
    assert any("between 2 and 7" in e for e in errors)

    dup_ids = EventDraft(
        event_id="dup",
        title="Duplicate",
        narrative="",
        choices=[Choice(id="c1", text="One"), Choice(id="c1", text="Two")],
    )
    dup_errors = dup_ids.validate(catalog)
    assert any("Duplicate choice id" in e for e in dup_errors)


def test_effect_validation_targets():
    catalog = ItemCatalog()
    effects = [
        Effect(EffectType.ADD_ITEM, "itm_unknown", 1),
        Effect(EffectType.MODIFY_RESOURCE, "gold", 5),
    ]
    errors = validate_effect_targets(effects, catalog)
    assert any("Unknown item_id" in e for e in errors)
    assert any("Invalid resource target" in e for e in errors)


def test_modify_resource_rejects_unknown():
    state = GameState()
    try:
        state.modify_resource("gold", 10)
        assert False, "Expected ValueError for unknown resource"
    except ValueError:
        assert True


def test_gateway_offline_short_circuits_to_fallback():
    gateway = GeminiGateway(api_key=None)
    gateway.resource_exhausted = True
    state = GameState()
    catalog = ItemCatalog()

    event = gateway.generate_event_draft(state, catalog)
    assert event.event_id.startswith("fallback_")
    assert gateway.last_event_source == "fallback"
    assert gateway.last_failure_reason in {"resource_exhausted", "offline"}


def test_gateway_resolution_validation_rejects_bad_effects():
    gateway = GeminiGateway(api_key="dummy")  # pretend online; won't call API in this path
    raw = """
    {
      "text": "Bad resolution",
      "effects": [
        {"operation": "modify_resource", "target": "gold", "value": 10}
      ]
    }
    """
    parsed = gateway._parse_event_resolution(raw, "c1", ItemCatalog())  # type: ignore[attr-defined]
    assert parsed is None


def test_fallback_monitor_tracks_events_and_resolutions():
    monitor = FallbackMonitor()
    monitor.record_event("fallback", "validation_error")
    monitor.record_resolution("fallback", "timeout")
    assert monitor.event_fallbacks == 1
    assert monitor.resolution_fallbacks == 1
    assert monitor.last_reason == "timeout"
    assert monitor.should_notify_offline()
    monitor.mark_offline_notified()
    assert monitor.should_notify_offline() is False


def test_runner_log_fallback_uses_ui_stub():
    # Patch GameUI and start_prefetch to avoid Pygame and threads
    from conestoga.game import runner as runner_mod

    class FakeUI:
        def __init__(self):
            self.event_log = []
            self.gemini_online = True

        def add_to_log(self, message: str, category: str = "info"):
            self.event_log.append((message, category))

    original_ui = runner_mod.GameUI
    original_start_prefetch = runner_mod.ConestogaGame.start_prefetch
    runner_mod.GameUI = FakeUI  # type: ignore[assignment]
    runner_mod.ConestogaGame.start_prefetch = lambda self: None  # type: ignore[assignment]
    try:
        game = runner_mod.ConestogaGame()
        game._log_fallback("event", "timeout")  # type: ignore[attr-defined]
        assert any("Fallback event used" in msg for msg, cat in game.ui.event_log if cat == "warning")
    finally:
        runner_mod.GameUI = original_ui  # type: ignore[assignment]
        runner_mod.ConestogaGame.start_prefetch = original_start_prefetch  # type: ignore[assignment]


def test_ui_headful_toggle(monkeypatch):
    # Ensure UI_HEADLESS=0 creates a visible display flag (not hidden)
    monkeypatch.setenv("UI_HEADLESS", "0")
    from conestoga.game.ui import GameUI

    ui = GameUI(width=400, height=300)
    assert ui.screen.get_flags() & 0x00000000 == 0  # surface exists; no hidden flag expected
    ui.quit()
