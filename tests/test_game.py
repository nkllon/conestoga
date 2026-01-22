"""Tests for Conestoga game systems"""
import pytest
from conestoga.game.state import GameState, ItemCatalog, PartyMember
from conestoga.game.events import (
    EventDraft, Choice, Prerequisite, Effect, EffectType,
    EventResolution, Outcome, FallbackDeck
)
from conestoga.game.gemini_gateway import GeminiGateway


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
        prerequisites=[Prerequisite(type="has_item", target="itm_rifle", value=1)]
    )
    assert choice2.is_available(state)
    
    choice3 = Choice(
        id="c3",
        text="Use shovel",
        prerequisites=[Prerequisite(type="has_item", target="itm_shovel", value=1)]
    )
    assert not choice3.is_available(state)


def test_event_validation():
    """Test event draft validation"""
    catalog = ItemCatalog()
    
    event1 = EventDraft(
        event_id="test1",
        title="Test Event",
        narrative="Test narrative",
        choices=[Choice(id="c1", text="Continue")]
    )
    errors1 = event1.validate(catalog)
    assert len(errors1) == 0
    
    event2 = EventDraft(
        event_id="",
        title="",
        narrative="",
        choices=[]
    )
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
    gateway = GeminiGateway(api_key=None)
    state = GameState()
    catalog = ItemCatalog()
    
    assert not gateway.is_online()
    
    event = gateway.generate_event_draft(state, catalog)
    assert event is not None
    assert event.event_id.startswith("fallback_")
