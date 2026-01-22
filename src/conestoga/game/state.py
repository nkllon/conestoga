"""
Game State - Authoritative state model for Conestoga
Implements Requirements 3.1, 3.2, 4.1, 4.6, 15.1
"""
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


class BiomeType(Enum):
    PRAIRIE = "prairie"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    RIVER = "river"


class WeatherType(Enum):
    CLEAR = "clear"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"


@dataclass
class PartyMember:
    """A member of the traveling party"""
    name: str
    health: int = 100  # 0-100
    morale: int = 100  # 0-100
    skill_hunter: int = 0  # 0-10
    skill_guide: int = 0  # 0-10
    skill_doctor: int = 0  # 0-10
    status_conditions: List[str] = field(default_factory=list)


@dataclass
class ItemCatalog:
    """Canonical item registry with stable IDs"""
    items: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.items:
            self.items = {
                "itm_shovel": "Shovel",
                "itm_rifle": "Rifle",
                "itm_medicine": "Medicine",
                "itm_wheel": "Wagon Wheel",
                "itm_axle": "Wagon Axle",
                "itm_rope": "Rope",
                "itm_blanket": "Blanket",
                "itm_cookware": "Cookware",
                "itm_spare_clothes": "Spare Clothes",
                "itm_tools": "Tools",
            }
    
    def has_item(self, item_id: str) -> bool:
        return item_id in self.items
    
    def get_name(self, item_id: str) -> str:
        return self.items.get(item_id, item_id)
    
    def add_item(self, item_id: str, display_name: str):
        if item_id not in self.items:
            self.items[item_id] = display_name


@dataclass
class GameState:
    """Authoritative game state"""
    day: int = 1
    miles_traveled: int = 0
    target_miles: int = 2000
    position_x: int = 0
    position_y: int = 0
    party: List[PartyMember] = field(default_factory=list)
    food: int = 500
    water: int = 100
    ammo: int = 50
    money: int = 200
    inventory: Dict[str, int] = field(default_factory=dict)
    biome: BiomeType = BiomeType.PRAIRIE
    weather: WeatherType = WeatherType.CLEAR
    wagon_health: int = 100
    flags: Dict[str, bool] = field(default_factory=dict)
    run_history_summary: List[str] = field(default_factory=list)
    is_game_over: bool = False
    victory: bool = False
    
    def __post_init__(self):
        if not self.party:
            self.party = [
                PartyMember("Sarah", skill_guide=5),
                PartyMember("John", skill_hunter=6),
                PartyMember("Mary", skill_doctor=4),
                PartyMember("Tom", skill_hunter=3),
            ]
        if not self.inventory:
            self.inventory = {
                "itm_rifle": 2,
                "itm_cookware": 1,
                "itm_blanket": 4,
                "itm_spare_clothes": 4,
            }
    
    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        return self.inventory.get(item_id, 0) >= quantity
    
    def add_item(self, item_id: str, quantity: int = 1):
        if quantity < 0:
            raise ValueError("Cannot add negative quantity")
        self.inventory[item_id] = self.inventory.get(item_id, 0) + quantity
    
    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        if quantity < 0:
            raise ValueError("Cannot remove negative quantity")
        if not self.has_item(item_id, quantity):
            return False
        self.inventory[item_id] -= quantity
        if self.inventory[item_id] <= 0:
            del self.inventory[item_id]
        return True
    
    def modify_resource(self, resource: str, delta: int):
        current = getattr(self, resource, 0)
        new_value = max(0, current + delta)
        setattr(self, resource, new_value)
    
    def advance_day(self, miles: int = 15):
        self.day += 1
        self.miles_traveled += miles
        self.modify_resource("food", -len(self.party) * 2)
        self.modify_resource("water", -len(self.party) * 1)
        
        if self.miles_traveled >= self.target_miles:
            self.is_game_over = True
            self.victory = True
        elif self.food <= 0 or all(m.health <= 0 for m in self.party):
            self.is_game_over = True
            self.victory = False
    
    def get_summary(self) -> Dict:
        return {
            "day": self.day,
            "miles": self.miles_traveled,
            "food": self.food,
            "water": self.water,
            "ammo": self.ammo,
            "money": self.money,
            "party_count": len([m for m in self.party if m.health > 0]),
            "party_health_avg": sum(m.health for m in self.party) // len(self.party) if self.party else 0,
            "inventory": list(self.inventory.keys()),
            "biome": self.biome.value,
            "weather": self.weather.value,
            "wagon_health": self.wagon_health,
            "flags": list(self.flags.keys()),
        }
