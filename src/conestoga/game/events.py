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
    MODIFY_PARTY_HEALTH = "modify_party_health"  # Affect specific party member
    MODIFY_RANDOM_HEALTH = "modify_random_health"  # Affect random party members
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
            elif self.operation == EffectType.MODIFY_PARTY_HEALTH:
                # Target specific member by name or index
                if isinstance(self.target, str):
                    member = next((m for m in game_state.party if m.name == self.target), None)
                    if member:
                        member.health = max(0, min(100, member.health + (self.value or 0)))
                elif isinstance(self.target, int) and 0 <= self.target < len(game_state.party):
                    game_state.party[self.target].health = max(0, min(100, game_state.party[self.target].health + (self.value or 0)))
            elif self.operation == EffectType.MODIFY_RANDOM_HEALTH:
                # Affect random party members (value = [health_change, num_affected])
                if isinstance(self.value, list) and len(self.value) == 2:
                    health_change, num_affected = self.value
                    affected = random.sample(game_state.party, min(num_affected, len(game_state.party)))
                    for member in affected:
                        member.health = max(0, min(100, member.health + health_change))
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
    success_effects: list[Effect] = field(default_factory=list)  # Extra effects only on success
    failure_effects: list[Effect] = field(default_factory=list)  # Extra effects only on failure


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

        if self.choices:
            if len(self.choices) < 2 or len(self.choices) > 7:
                errors.append("Choices must be between 2 and 7 options")

            seen_ids = set()
            for choice in self.choices:
                if not choice.id:
                    errors.append("Choice id is required")
                if choice.id in seen_ids:
                    errors.append(f"Duplicate choice id: {choice.id}")
                seen_ids.add(choice.id)
                if not choice.text or not choice.text.strip():
                    errors.append(f"Choice text missing for id {choice.id or '<unknown>'}")

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
        success = True  # Default to success if no check required
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

        # Apply base effects (always happen)
        for effect in self.outcome.effects:
            if not effect.apply(game_state):
                print(f"Warning: Effect {effect.operation} failed to apply")
        
        # Apply conditional effects based on success/failure
        if success and self.outcome.success_effects:
            for effect in self.outcome.success_effects:
                if not effect.apply(game_state):
                    print(f"Warning: Success effect {effect.operation} failed to apply")
        elif not success and self.outcome.failure_effects:
            for effect in self.outcome.failure_effects:
                if not effect.apply(game_state):
                    print(f"Warning: Failure effect {effect.operation} failed to apply")

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
                    Choice(id="collect_water", text="Stop to collect water barrels"),
                ],
            ),
            EventDraft(
                event_id="fallback_hunting",
                title="Wildlife Spotted",
                narrative="Deer tracks cross your path. A hunting party could gather fresh meat, but the wilderness is unpredictable.",
                choices=[
                    Choice(
                        id="hunt",
                        text="Send hunters after the game",
                        prerequisites=[Prerequisite(type="has_item", target="itm_rifle", value=1)],
                    ),
                    Choice(id="continue", text="Continue on the trail"),
                ],
            ),
            EventDraft(
                event_id="fallback_trader",
                title="Traveling Trader",
                narrative="A lone trader offers to sell supplies. His prices are higher than at forts.",
                choices=[
                    Choice(
                        id="buy_food",
                        text="Buy food (25 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=25)],
                    ),
                    Choice(
                        id="buy_water",
                        text="Buy water barrels (15 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=15)],
                    ),
                    Choice(
                        id="buy_rope",
                        text="Buy rope (10 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=10)],
                    ),
                    Choice(id="decline", text="Decline and move on"),
                ],
            ),
            EventDraft(
                event_id="fallback_fort",
                title="Trading Fort",
                narrative="You arrive at a well-stocked fort. Prices are reasonable and variety is good.",
                choices=[
                    Choice(
                        id="buy_supplies",
                        text="Buy bulk supplies (50 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=50)],
                    ),
                    Choice(
                        id="buy_medicine",
                        text="Buy medicine (25 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=25)],
                    ),
                    Choice(
                        id="buy_wagon_parts",
                        text="Buy wagon parts (40 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=40)],
                    ),
                    Choice(
                        id="buy_tools",
                        text="Buy rope & tools (20 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=20)],
                    ),
                    Choice(
                        id="buy_clothes",
                        text="Buy spare clothes (15 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=15)],
                    ),
                    Choice(
                        id="buy_ammo",
                        text="Buy ammunition (20 coins)",
                        prerequisites=[Prerequisite(type="min_resource", target="money", value=20)],
                    ),
                    Choice(id="leave", text="Leave the fort"),
                ],
            ),
            EventDraft(
                event_id="fallback_rest",
                title="Rest Stop",
                narrative="The party is weary. A day of rest might improve morale and health.",
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
                    Choice(id="collect_rain", text="Set out barrels to collect rainwater"),
                    Choice(id="continue_travel", text="Continue traveling through the storm"),
                ],
            ),
            EventDraft(
                event_id="fallback_illness",
                title="Sickness Strikes",
                narrative="One of your party members has fallen ill with a fever.",
                choices=[
                    Choice(
                        id="use_medicine",
                        text="Use medicine",
                        prerequisites=[Prerequisite(type="has_item", target="itm_medicine", value=1)],
                    ),
                    Choice(id="rest_it_off", text="Rest and hope they recover"),
                    Choice(id="continue_anyway", text="Continue traveling despite illness"),
                ],
            ),
        ]

    def _create_resolutions(self) -> dict[str, dict[str, EventResolution]]:
        return {
            "fallback_river_crossing": {
                "ford": EventResolution(
                    choice_id="ford",
                    outcome=Outcome(
                        text="The crossing goes smoothly, though one person slips and gets soaked.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "water", 10),
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-5, 1]),  # 1 person loses 5 health
                        ],
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
                "collect_water": EventResolution(
                    choice_id="collect_water",
                    outcome=Outcome(
                        text="",
                        success_required={"random": True, "dc": 12},  # ~45% chance of contamination
                        success_text="You fill barrels with fresh, clear water from the river.",
                        failure_text="The water looked clean, but one family member falls ill from contamination.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "water", 35),
                        ],
                        failure_effects=[
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-15, 1]),  # 1 person gets sick from bad water
                        ],
                    ),
                ),
            },
            "fallback_hunting": {
                "hunt": EventResolution(
                    choice_id="hunt",
                    outcome=Outcome(
                        text="",
                        success_required={"skill": "hunter", "dc": 14},  # Increased difficulty
                        success_text="Your hunters bring down a buck! Fresh meat for the party.",
                        failure_text="The hunt goes poorly. A hunter is injured and the rifle is damaged in the scramble.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "ammo", -3),  # Always use ammo
                        ],
                        success_effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "food", 50),  # Good haul on success
                        ],
                        failure_effects=[
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-15, 1]),  # 1 hunter gets hurt
                            Effect(EffectType.REMOVE_ITEM, "itm_rifle", 1),  # Rifle broken/lost
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
                        text="You purchase food supplies from the trader at a premium price.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -25),
                            Effect(EffectType.MODIFY_RESOURCE, "food", 40),
                        ],
                    ),
                ),
                "buy_water": EventResolution(
                    choice_id="buy_water",
                    outcome=Outcome(
                        text="You purchase water barrels from the trader.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -15),
                            Effect(EffectType.MODIFY_RESOURCE, "water", 30),
                        ],
                    ),
                ),
                "buy_rope": EventResolution(
                    choice_id="buy_rope",
                    outcome=Outcome(
                        text="You purchase rope from the trader.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -10),
                            Effect(EffectType.ADD_ITEM, "itm_rope", 1),
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
            "fallback_fort": {
                "buy_supplies": EventResolution(
                    choice_id="buy_supplies",
                    outcome=Outcome(
                        text="You stock up on food and water at fair fort prices.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -50),
                            Effect(EffectType.MODIFY_RESOURCE, "food", 80),
                            Effect(EffectType.MODIFY_RESOURCE, "water", 50),
                        ],
                    ),
                ),
                "buy_medicine": EventResolution(
                    choice_id="buy_medicine",
                    outcome=Outcome(
                        text="You purchase medicine from the fort's well-stocked store.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -25),
                            Effect(EffectType.ADD_ITEM, "itm_medicine", 3),
                        ],
                    ),
                ),
                "buy_wagon_parts": EventResolution(
                    choice_id="buy_wagon_parts",
                    outcome=Outcome(
                        text="The blacksmith repairs your wagon with quality parts.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -40),
                            Effect(EffectType.REPAIR_WAGON, None, 30),
                        ],
                    ),
                ),
                "buy_tools": EventResolution(
                    choice_id="buy_tools",
                    outcome=Outcome(
                        text="You purchase rope and tools for repairs.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -20),
                            Effect(EffectType.ADD_ITEM, "itm_rope", 2),
                            Effect(EffectType.ADD_ITEM, "itm_tools", 1),
                        ],
                    ),
                ),
                "buy_clothes": EventResolution(
                    choice_id="buy_clothes",
                    outcome=Outcome(
                        text="You buy spare clothes to keep the family warm and dry.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -15),
                            Effect(EffectType.ADD_ITEM, "itm_spare_clothes", 4),
                        ],
                    ),
                ),
                "buy_ammo": EventResolution(
                    choice_id="buy_ammo",
                    outcome=Outcome(
                        text="You purchase ammunition for hunting.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "money", -20),
                            Effect(EffectType.MODIFY_RESOURCE, "ammo", 25),
                        ],
                    ),
                ),
                "leave": EventResolution(
                    choice_id="leave",
                    outcome=Outcome(
                        text="You depart the fort and continue westward.", effects=[]
                    ),
                ),
            },
            "fallback_rest": {
                "rest": EventResolution(
                    choice_id="rest",
                    outcome=Outcome(
                        text="The party rests and recovers. Everyone feels better, though a day is lost.",
                        effects=[
                            Effect(EffectType.ADVANCE_TIME, None, 1),  # Advance 1 day
                            Effect(EffectType.MODIFY_RESOURCE, "food", -8),  # Daily consumption
                            Effect(EffectType.MODIFY_RESOURCE, "water", -4),  # Daily consumption
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [15, 4]),  # All 4 members gain health
                            Effect(EffectType.LOG_JOURNAL, "Took a rest day to recover."),
                        ],
                    ),
                ),
                "push_on": EventResolution(
                    choice_id="push_on",
                    outcome=Outcome(
                        text="You push the weary party onward. The exhaustion worsens their condition.",
                        effects=[
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-8, 3]),  # 3 members lose more health
                        ],
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
                "collect_rain": EventResolution(
                    choice_id="collect_rain",
                    outcome=Outcome(
                        text="",
                        success_required={"random": True, "dc": 14},  # ~35% chance of contamination
                        success_text="You collect fresh rainwater in barrels during the storm.",
                        failure_text="The rainwater collected debris and someone gets sick from drinking it.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "water", 20),  # Less water than river
                            Effect(EffectType.MODIFY_RESOURCE, "food", -4),  # Time spent
                        ],
                        failure_effects=[
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-10, 1]),  # 1 person gets sick
                        ],
                    ),
                ),
                "continue_travel": EventResolution(
                    choice_id="continue_travel",
                    outcome=Outcome(
                        text="You travel through the storm. The wagon takes damage and someone catches a chill.",
                        effects=[
                            Effect(EffectType.DAMAGE_WAGON, None, 15),
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-10, 1]),
                        ],
                    ),
                ),
            },
            "fallback_illness": {
                "use_medicine": EventResolution(
                    choice_id="use_medicine",
                    outcome=Outcome(
                        text="The medicine works quickly. Your companion recovers fully.",
                        effects=[
                            Effect(EffectType.REMOVE_ITEM, "itm_medicine", 1),
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [20, 1]),
                        ],
                    ),
                ),
                "rest_it_off": EventResolution(
                    choice_id="rest_it_off",
                    outcome=Outcome(
                        text="With rest, your companion slowly recovers, though they're still weak.",
                        effects=[
                            Effect(EffectType.MODIFY_RESOURCE, "food", -6),
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [5, 1]),
                        ],
                    ),
                ),
                "continue_anyway": EventResolution(
                    choice_id="continue_anyway",
                    outcome=Outcome(
                        text="Pressing on makes the illness worse. Your companion deteriorates.",
                        effects=[
                            Effect(EffectType.MODIFY_RANDOM_HEALTH, None, [-15, 1]),
                        ],
                    ),
                ),
            },
        }

    def get_random_event(self, game_state) -> EventDraft:
        return random.choice(self.events)

    def get_resolution(self, event_id: str, choice_id: str) -> EventResolution | None:
        return self.resolutions.get(event_id, {}).get(choice_id)
