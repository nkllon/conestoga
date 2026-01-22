"""
Conestoga - Main Game Runner
Entry point for the Conestoga game
"""
import pygame
import random
from enum import Enum
from typing import Optional

from .state import GameState, ItemCatalog
from .events import EventDraft, FallbackDeck
from .gemini_gateway import GeminiGateway
from .ui import GameUI


class GameMode(Enum):
    """Game state machine modes"""
    TRAVEL = "travel"
    EVENT = "event"
    RESOLUTION = "resolution"
    INVENTORY = "inventory"
    GAME_OVER = "game_over"


class ConestogaGame:
    """Main game controller"""
    
    def __init__(self):
        self.game_state = GameState()
        self.item_catalog = ItemCatalog()
        self.gemini = GeminiGateway()
        self.ui = GameUI()
        
        self.mode = GameMode.TRAVEL
        self.current_event: Optional[EventDraft] = None
        self.current_resolution: Optional[str] = None
        self.selected_choice_index = 0
        
        self.days_since_event = 0
        self.event_frequency = 3
        
        print("=" * 60)
        print("CONESTOGA - Oregon Trail Journey Simulation")
        print("=" * 60)
        print(f"Gemini API: {'ONLINE' if self.gemini.is_online() else 'OFFLINE (Fallback Mode)'}")
        print(f"Starting journey to Oregon - {self.game_state.target_miles} miles ahead!")
        print("=" * 60)
    
    def should_trigger_event(self) -> bool:
        self.days_since_event += 1
        chance = min(0.8, self.days_since_event / self.event_frequency)
        return random.random() < chance
    
    def trigger_event(self):
        print(f"\n[Day {self.game_state.day}] Event triggered!")
        
        self.current_event = self.gemini.generate_event_draft(
            self.game_state,
            self.item_catalog,
            tier="minor"
        )
        
        errors = self.current_event.validate(self.item_catalog)
        if errors:
            print(f"[Warning] Event validation errors: {errors}")
            fallback = FallbackDeck()
            self.current_event = fallback.get_random_event(self.game_state)
        
        self.selected_choice_index = 0
        self.mode = GameMode.EVENT
        self.days_since_event = 0
        print(f"Event: {self.current_event.title}")
    
    def resolve_choice(self, choice_index: int):
        if not self.current_event:
            return
        
        choice = self.current_event.choices[choice_index]
        
        if not choice.is_available(self.game_state):
            print(f"[Warning] Choice not available: {choice.get_lock_reason(self.game_state)}")
            return
        
        print(f"[Choice] Selected: {choice.text}")
        
        resolution = self.gemini.generate_event_resolution(
            self.current_event,
            choice.id,
            self.game_state
        )
        
        if not resolution:
            self.current_resolution = "You make your choice and move on."
        else:
            self.current_resolution = resolution.apply(self.game_state)
            print(f"[Resolution] {self.current_resolution}")
        
        self.mode = GameMode.RESOLUTION
    
    def advance_travel(self):
        print(f"\n--- Day {self.game_state.day + 1} ---")
        
        miles_today = random.randint(12, 18)
        self.game_state.advance_day(miles_today)
        
        print(f"Traveled {miles_today} miles. Total: {self.game_state.miles_traveled}/{self.game_state.target_miles}")
        print(f"Food: {self.game_state.food}, Water: {self.game_state.water}")
        
        if self.game_state.is_game_over:
            self.mode = GameMode.GAME_OVER
            if self.game_state.victory:
                print("\n*** VICTORY! You reached Oregon! ***")
            else:
                print("\n*** GAME OVER ***")
            return
        
        if self.should_trigger_event():
            self.trigger_event()
    
    def handle_travel_input(self, key: int):
        if key == pygame.K_SPACE:
            self.advance_travel()
        elif key == pygame.K_i:
            self.mode = GameMode.INVENTORY
        elif key == pygame.K_q:
            self.ui.running = False
    
    def handle_event_input(self, key: int):
        if not self.current_event:
            return
        
        if key == pygame.K_UP:
            self.selected_choice_index = (self.selected_choice_index - 1) % len(self.current_event.choices)
        elif key == pygame.K_DOWN:
            self.selected_choice_index = (self.selected_choice_index + 1) % len(self.current_event.choices)
        elif key == pygame.K_RETURN:
            self.resolve_choice(self.selected_choice_index)
        elif key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
            choice_num = key - pygame.K_1
            if choice_num < len(self.current_event.choices):
                self.selected_choice_index = choice_num
                self.resolve_choice(choice_num)
    
    def handle_resolution_input(self, key: int):
        if key == pygame.K_SPACE:
            self.current_event = None
            self.current_resolution = None
            self.mode = GameMode.TRAVEL
    
    def handle_inventory_input(self, key: int):
        if key == pygame.K_ESCAPE:
            self.mode = GameMode.TRAVEL
    
    def handle_gameover_input(self, key: int):
        if key == pygame.K_r:
            self.game_state = GameState()
            self.mode = GameMode.TRAVEL
            self.days_since_event = 0
            print("\n\n" + "=" * 60)
            print("NEW JOURNEY STARTED")
            print("=" * 60)
        elif key == pygame.K_q:
            self.ui.running = False
    
    def run(self):
        """Main game loop"""
        while self.ui.running:
            key = self.ui.handle_events()
            
            if key:
                if self.mode == GameMode.TRAVEL:
                    self.handle_travel_input(key)
                elif self.mode == GameMode.EVENT:
                    self.handle_event_input(key)
                elif self.mode == GameMode.RESOLUTION:
                    self.handle_resolution_input(key)
                elif self.mode == GameMode.INVENTORY:
                    self.handle_inventory_input(key)
                elif self.mode == GameMode.GAME_OVER:
                    self.handle_gameover_input(key)
            
            if self.mode == GameMode.TRAVEL:
                self.ui.render_travel_screen(self.game_state)
            elif self.mode == GameMode.EVENT:
                if self.current_event:
                    self.ui.render_event_screen(self.current_event, self.game_state, self.selected_choice_index)
            elif self.mode == GameMode.RESOLUTION:
                if self.current_resolution:
                    self.ui.render_resolution_screen(self.current_resolution)
            elif self.mode == GameMode.INVENTORY:
                self.ui.render_inventory_screen(self.game_state, self.item_catalog)
            elif self.mode == GameMode.GAME_OVER:
                self.ui.render_game_over_screen(self.game_state)
            
            self.ui.update()
        
        self.ui.quit()
        print("\nThanks for playing Conestoga!")


def main():
    """Entry point for the game"""
    game = ConestogaGame()
    game.run()


if __name__ == "__main__":
    main()
