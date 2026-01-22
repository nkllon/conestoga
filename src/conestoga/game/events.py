"""
Event System - EventDrafts, EventResolutions, and Fallback Deck
Implements Requirements 5.1-5.6, 6.1-6.4, 8.1, 9.3, 13.1
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EffectType(Enum):
    """Whitelisted effect operations"""

    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    MODIFY_RESOURCE = "modify_resource"
    MODIFY_STAT = "modify_stat"
    SET_FLAG = "set_flag"
    CLEAR_FLAG = "clear_flag"
    ADVANCE_TIME = "advance_time"
    DAMAGE_WAGON = "damage_wagon"
    REPAIR_WAGON = "repair_wagon"
    LOG_JOURNAL = "log_journal"
    QUEUE_FOLLOWUP = "queue_followup"


@dataclass
class Prerequisite:
    """Requirement for a choice to be available"""

    type: str
    target: str | None = None
    value: int | None = None

    def is_met(self, game_state) -> bool:
        if self.type == "has_item":
            return game_state.has_item(self.target, self.value or 1)
        elif self.type == "min_resource":
            return getattr(game_state, self.target, 0) >= (self.value or 0)
        elif self.type == "flag_set":
            return game_state.flags.get(self.target, False)
        elif self.type == "skill_check":
            return any(
                getattr(m, f"skill_{self.target}", 0) >= (self.value or 0) for m in game_state.party
            )
        return True

    def get_reason(self) -> str:
        if self.type == "has_item":
            return f"Requires: {self.target} x{self.value or 1}"
        elif self.type == "min_resource":
            return f"Requires: {self.target} >= {self.value}"
        elif self.type == "flag_set":
            return f"Requires: {self.target}"
        elif self.type == "skill_check":
            return f"Requires: {self.target} skill >= {self.value}"
        return "Requirements not met"


@dataclass
class Effect:
    """State mutation effect"""

    operation: EffectType
    target: str | None = None
    value: Any | None = None

    def apply(self, game_state) -> bool:
        try:
            if self.operation == EffectType.ADD_ITEM:
                game_state.add_item(self.target, self.value or 1)
            elif self.operation == EffectType.REMOVE_ITEM:
                return game_state.remove_item(self.target, self.value or 1)
            elif self.operation == EffectType.MODIFY_RESOURCE:
                game_state.modify_resource(self.target, self.value or 0)
            elif self.operation == EffectType.SET_FLAG:
                game_state.flags[self.target] = True
            elif self.operation == EffectType.CLEAR_FLAG:
                game_state.flags.pop(self.target, None)
            elif self.operation == EffectType.DAMAGE_WAGON:
                game_state.wagon_health = max(0, game_state.wagon_health - (self.value or 10))
            elif self.operation == EffectType.REPAIR_WAGON:
                game_state.wagon_health = min(100, game_state.wagon_health + (self.value or 10))
            elif self.operation == EffectType.LOG_JOURNAL:
                if self.target:
                    game_state.run_history_summary.append(self.target)
            return True
        except Exception as e:
            print(f"Effect application failed: {e}")
            return False


@dataclass
class Choice:
    """Player choice option"""

    id: str
    text: str
    prerequisites: list[Prerequisite] = field(default_factory=list)

    def is_available(self, game_state) -> bool:
        return all(p.is_met(game_state) for p in self.prerequisites)

    def get_lock_reason(self, game_state) -> str | None:
        for p in self.prerequisites:
            if not p.is_met(game_state):
                return p.get_reason()
        return None


@dataclass
class Outcome:
    """Result of a choice"""

    text: str
    effects: list[Effect] = field(default_factory=list)
    success_required: dict[str, int] | None = None
    success_text: str | None = None
    failure_text: str | None = None


@dataclass
class EventDraft:
    """LLM-generated event draft"""

    event_id: str
    title: str
    narrative: str
    choices: list[Choice]
    tier: str = "minor"

    def validate(self, item_catalog) -> list[str]:
        errors = []
        if not self.event_id:
            errors.append("Missing event_id")
        if not self.title:
            errors.append("Missing title")
        if not self.narrative:
            errors.append("Missing narrative")
        if not self.choices:
            errors.append("No choices provided")

        for choice in self.choices:
            for prereq in choice.prerequisites:
                if prereq.type == "has_item" and prereq.target:
                    if not item_catalog.has_item(prereq.target):
                        errors.append(f"Unknown item_id: {prereq.target}")
        return errors


@dataclass
class EventResolution:
    """Resolution of a choice"""

    choice_id: str
    outcome: Outcome

    def apply(self, game_state, rng_seed: int | None = None) -> str:
        if self.outcome.success_required:
            skill = self.outcome.success_required.get("skill")
            dc = self.outcome.success_required.get("dc", 10)

            rng = random.Random(rng_seed) if rng_seed else random
            party_skill = max(getattr(m, f"skill_{skill}", 0) for m in game_state.party)
            roll = rng.randint(1, 20)
            success = (roll + party_skill) >= dc

            result_text = self.outcome.success_text if success else self.outcome.failure_text
        else:
            result_text = self.outcome.text

        for effect in self.outcome.effects:
            if not effect.apply(game_state):
                print(f"Warning: Effect {effect.operation} failed to apply")

        return result_text or "The journey continues..."


class FallbackDeck:
    """Local deterministic event deck"""

    def __init__(self):
        self.events = self._create_fallback_events()
        self.resolutions = self._create_resolutions()

    def _create_fallback_events(self) -> list[EventDraft]:
        return [
            EventDraft(
                event_id="fallback_river_crossing",
                title="River Crossing",
                narrative="You reach a shallow river. The water is cold but the current is gentle.",
                choices=[
                    Choice(id="ford", text="Ford the river carefully"),
                    Choice(
                        id="use_rope",
                        text="Use rope to secure the wagon",
                        prerequisites=[Prerequisite(type="has_item", target="itm_rope", value=1)],
                    ),
                ],
            ),
            EventDraft(
                event_id="fallback_hunting",
                title="Wildlife Spotted",
                narrative="Deer tracks cross your path. A hunting party could gather fresh meat.",
                choices=[
                    Choice(
                        id="hunt",
                        text="Hunt for food",
                        prerequisites=[Prerequisite(type="has_item", target="itm_rifle", value=1)],
                    ),
                    Choice(id="continue", text="Continue on the trail"),
                ],
            ),
            EventDraft(
                event_id="fallback_trader",
                title="Traveling Trader",
                narrative="A lone trader offers to sell supplies. His prices are fair.",
                choices=[
                    Choice(
                        id="buy_food",
                        text="Buy food (20 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=20)],
                    ),
                    Choice(
                        id="buy_medicine",
                        text="Buy medicine (30 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=30)],
                    ),
                    Choice(id="decline", text="Decline and move on"),
                ],
            ),
            EventDraft(
                event_id="fallback_rest",
                title="Rest Stop",
                narrative="The party is weary. A day of rest might improve morale.",
                choices=[
                    Choice(id="rest", text="Rest for a day"),
                    Choice(id="push_on", text="Push on despite fatigue"),
                ],
            ),
            EventDraft(
                event_id="fallback_weather",
                title="Storm Clouds",
                narrative="Dark clouds gather on the horizon. A storm is approaching.",
                choices=[
                    Choice(id="seek_shelter", text="Seek shelter and wait it out"),
                    Choice(id="continue_travel", text="Continue traveling through the storm"),
                ],
            ),
        ]

    def _create_resolutions(self) -> dict[str, dict[str, EventResolution]]:
        return {
            "fallback_river_crossing": {
                "ford": EventResolution(
                    choice_id="ford",
                    outcome=Outcome(
                        text="You ford the river safely. The wagon gets wet but no damage is done.",
                        effects=[Effect(EffectType.MODIFY_RESOURCE, "water", 10)],
                    ),
                ),
                "use_rope": EventResolution(
                    choice_id="use_rope",
                    outcome=Outcome(
                        text="Using the rope, you secure the wagon and cross without incident.",
                        effects=[
                            Effect(EffectType.REMOVE_ITEM, "itm_rope", 1),
                            Effect(EffectType.MODIFY_RESOURCE, "water", 15),
                        ],
                    ),
                ),
            },
            "fallback_hunting": {
                "hunt": EventResolution(
                    choice_id="hunt",
                    outcome=Outcome(
                        text="",
                        success_required={"skill": "hunter", "dc": 12},
                        success_text="Your hunters bring down a deer! Fresh meat for the party.",
                        failure_text="The hunting party returns empty-handed.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "ammo", -3),
                            Effect(EffectType.MODIFY_RESOURCE, "food", 40),
                        ],
                    ),
                ),
                "continue": EventResolution(
                    choice_id="continue",
                    outcome=Outcome(
                        text="You continue down the trail, leaving the wildlife undisturbed.",
                        effects=[],
                    ),
                ),
            },
            "fallback_trader": {
                "buy_food": EventResolution(
                    choice_id="buy_food",
                    outcome=Outcome(
                        text="You purchase food supplies from the trader.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -20),
                            Effect(EffectType.MODIFY_RESOURCE, "food", 50),
                        ],
                    ),
                ),
                "buy_medicine": EventResolution(
                    choice_id="buy_medicine",
                    outcome=Outcome(
                        text="You purchase medicine from the trader.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -30),
                            Effect(EffectType.ADD_ITEM, "itm_medicine", 2),
                        ],
                    ),
                ),
                "decline": EventResolution(
                    choice_id="decline",
                    outcome=Outcome(
                        text="You thank the trader and continue on your way.", effects=[]
                    ),
                ),
            },
            "fallback_rest": {
                "rest": EventResolution(
                    choice_id="rest",
                    outcome=Outcome(
                        text="The party rests and recovers. Morale improves.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "food", -8),
                            Effect(EffectType.LOG_JOURNAL, "Took a rest day to recover."),
                        ],
                    ),
                ),
                "push_on": EventResolution(
                    choice_id="push_on",
                    outcome=Outcome(
                        text="You push the party onward. They're tired but making progress.",
                        effects=[],
                    ),
                ),
            },
            "fallback_weather": {
                "seek_shelter": EventResolution(
                    choice_id="seek_shelter",
                    outcome=Outcome(
                        text="You find shelter and wait out the storm. No damage to the wagon.",
                        effects=[Effect(EffectType.MODIFY_RESOURCE, "food", -4)],
                    ),
                ),
                "continue_travel": EventResolution(
                    choice_id="continue_travel",
                    outcome=Outcome(
                        text="You travel through the storm. The wagon takes minor damage.",
                        effects=[Effect(EffectType.DAMAGE_WAGON, None, 15)],
                    ),
                ),
            },
        }

    def get_random_event(self, game_state) -> EventDraft:
        return random.choice(self.events)

    def get_resolution(self, event_id: str, choice_id: str) -> EventResolution | None:
        return self.resolutions.get(event_id, {}).get(choice_id)
