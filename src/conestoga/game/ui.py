"""
Pygame UI - Main game interface
Implements Requirements 1.3, 2.1, 10.2, 22.1-22.4
"""
import pygame
from typing import Optional, Tuple

from .state import GameState, ItemCatalog
from .events import EventDraft

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GREEN = (34, 139, 34)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
RED = (220, 20, 60)
BLUE = (70, 130, 180)
YELLOW = (255, 215, 0)
DARK_GRAY = (64, 64, 64)


class GameUI:
    """Main UI controller for Conestoga"""
    
    def __init__(self, width: int = 1024, height: int = 768):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Conestoga - Oregon Trail Journey")
        
        self.title_font = pygame.font.Font(None, 48)
        self.heading_font = pygame.font.Font(None, 36)
        self.body_font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)
        
        self.clock = pygame.time.Clock()
        self.running = True
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return None
            elif event.type == pygame.KEYDOWN:
                return event.key
        return None
    
    def draw_text(self, text: str, font: pygame.font.Font, color: Tuple, x: int, y: int, 
                  center: bool = False, max_width: Optional[int] = None):
        if max_width:
            words = text.split(' ')
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            for i, line in enumerate(lines):
                surface = font.render(line, True, color)
                if center:
                    rect = surface.get_rect(center=(x, y + i * font.get_height()))
                else:
                    rect = surface.get_rect(topleft=(x, y + i * font.get_height()))
                self.screen.blit(surface, rect)
            return len(lines) * font.get_height()
        else:
            surface = font.render(text, True, color)
            if center:
                rect = surface.get_rect(center=(x, y))
            else:
                rect = surface.get_rect(topleft=(x, y))
            self.screen.blit(surface, rect)
            return font.get_height()
    
    def draw_panel(self, x: int, y: int, width: int, height: int, color: Tuple, border_color: Tuple):
        pygame.draw.rect(self.screen, color, (x, y, width, height))
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), 3)
    
    def render_travel_screen(self, game_state: GameState):
        self.screen.fill(DARK_GREEN)
        
        self.draw_text("CONESTOGA", self.title_font, YELLOW, self.width // 2, 30, center=True)
        self.draw_text("The Oregon Trail Journey", self.small_font, WHITE, self.width // 2, 70, center=True)
        
        self.draw_panel(50, 120, self.width - 100, 200, BROWN, YELLOW)
        
        y_offset = 140
        self.draw_text(f"Day {game_state.day}  |  Miles: {game_state.miles_traveled} / {game_state.target_miles}", 
                      self.heading_font, WHITE, 70, y_offset)
        y_offset += 40
        
        self.draw_text(f"Location: {game_state.biome.value.title()}  |  Weather: {game_state.weather.value.title()}", 
                      self.body_font, LIGHT_GRAY, 70, y_offset)
        y_offset += 40
        
        self.draw_text(f"Food: {game_state.food}  Water: {game_state.water}  Ammo: {game_state.ammo}  Money: ${game_state.money}", 
                      self.body_font, WHITE, 70, y_offset)
        y_offset += 35
        
        self.draw_text(f"Wagon Health: {game_state.wagon_health}%", 
                      self.body_font, WHITE if game_state.wagon_health > 50 else RED, 70, y_offset)
        
        self.draw_panel(50, 350, self.width - 100, 200, DARK_GRAY, WHITE)
        self.draw_text("Party Status", self.heading_font, YELLOW, 70, 365)
        
        y_offset = 410
        for member in game_state.party:
            health_color = WHITE if member.health > 50 else (YELLOW if member.health > 20 else RED)
            status_text = f"{member.name}: Health {member.health}%"
            if member.status_conditions:
                status_text += f" [{', '.join(member.status_conditions)}]"
            self.draw_text(status_text, self.small_font, health_color, 70, y_offset)
            y_offset += 30
        
        self.draw_panel(50, 580, self.width - 100, 150, BLACK, WHITE)
        self.draw_text("Press SPACE to continue travel", self.body_font, WHITE, 70, 600)
        self.draw_text("Press I to view inventory", self.body_font, WHITE, 70, 635)
        self.draw_text("Press Q to quit", self.body_font, WHITE, 70, 670)
        
    def render_event_screen(self, event: EventDraft, game_state: GameState, selected_choice: int = 0):
        self.screen.fill(BLACK)
        
        self.draw_text(event.title, self.title_font, YELLOW, self.width // 2, 40, center=True)
        
        self.draw_panel(50, 100, self.width - 100, 200, DARK_GRAY, WHITE)
        self.draw_text(event.narrative, self.body_font, WHITE, 70, 120, max_width=self.width - 140)
        
        self.draw_text("Choose your action:", self.heading_font, YELLOW, 70, 330)
        
        y_offset = 380
        for i, choice in enumerate(event.choices):
            is_available = choice.is_available(game_state)
            is_selected = i == selected_choice
            
            choice_height = 60
            bg_color = BLUE if is_selected else DARK_GRAY
            if not is_available:
                bg_color = GRAY
            
            self.draw_panel(50, y_offset, self.width - 100, choice_height, bg_color, YELLOW if is_selected else WHITE)
            
            choice_text = f"{i + 1}. {choice.text}"
            text_color = WHITE if is_available else DARK_GRAY
            self.draw_text(choice_text, self.body_font, text_color, 70, y_offset + 10, max_width=self.width - 140)
            
            if not is_available:
                lock_reason = choice.get_lock_reason(game_state)
                if lock_reason:
                    self.draw_text(f"  {lock_reason}", self.small_font, RED, 70, y_offset + 35)
            
            y_offset += choice_height + 10
        
        y_offset += 20
        self.draw_text("Use UP/DOWN arrows to select, ENTER to confirm", self.small_font, LIGHT_GRAY, self.width // 2, y_offset, center=True)
    
    def render_resolution_screen(self, resolution_text: str):
        self.screen.fill(BLACK)
        
        self.draw_text("Outcome", self.title_font, YELLOW, self.width // 2, 40, center=True)
        
        self.draw_panel(50, 150, self.width - 100, 400, DARK_GRAY, WHITE)
        self.draw_text(resolution_text, self.body_font, WHITE, 70, 180, max_width=self.width - 140)
        
        self.draw_text("Press SPACE to continue...", self.body_font, YELLOW, self.width // 2, 600, center=True)
    
    def render_game_over_screen(self, game_state: GameState):
        self.screen.fill(BLACK)
        
        if game_state.victory:
            title = "Victory!"
            message = f"You reached Oregon after {game_state.day} days!"
            color = YELLOW
        else:
            title = "Game Over"
            if game_state.food <= 0:
                message = "Your party starved on the trail."
            else:
                message = "Your party did not survive the journey."
            color = RED
        
        self.draw_text(title, self.title_font, color, self.width // 2, 200, center=True)
        self.draw_text(message, self.heading_font, WHITE, self.width // 2, 270, center=True)
        
        y_offset = 350
        self.draw_text(f"Days Traveled: {game_state.day}", self.body_font, WHITE, self.width // 2, y_offset, center=True)
        y_offset += 40
        self.draw_text(f"Miles Covered: {game_state.miles_traveled}", self.body_font, WHITE, self.width // 2, y_offset, center=True)
        y_offset += 40
        survivors = len([m for m in game_state.party if m.health > 0])
        self.draw_text(f"Survivors: {survivors} / {len(game_state.party)}", self.body_font, WHITE, self.width // 2, y_offset, center=True)
        
        self.draw_text("Press R to restart or Q to quit", self.body_font, YELLOW, self.width // 2, 550, center=True)
    
    def render_inventory_screen(self, game_state: GameState, item_catalog: ItemCatalog):
        self.screen.fill(BLACK)
        
        self.draw_text("Inventory", self.title_font, YELLOW, self.width // 2, 40, center=True)
        
        self.draw_panel(50, 120, self.width - 100, 150, DARK_GRAY, WHITE)
        self.draw_text("Resources", self.heading_font, YELLOW, 70, 135)
        y_offset = 175
        self.draw_text(f"Food: {game_state.food} lbs", self.body_font, WHITE, 70, y_offset)
        self.draw_text(f"Water: {game_state.water} gallons", self.body_font, WHITE, 400, y_offset)
        y_offset += 35
        self.draw_text(f"Ammunition: {game_state.ammo} rounds", self.body_font, WHITE, 70, y_offset)
        self.draw_text(f"Money: ${game_state.money}", self.body_font, WHITE, 400, y_offset)
        
        self.draw_panel(50, 300, self.width - 100, 350, DARK_GRAY, WHITE)
        self.draw_text("Items", self.heading_font, YELLOW, 70, 315)
        
        y_offset = 360
        if game_state.inventory:
            for item_id, quantity in sorted(game_state.inventory.items()):
                item_name = item_catalog.get_name(item_id)
                self.draw_text(f"{item_name} x{quantity}", self.body_font, WHITE, 70, y_offset)
                y_offset += 35
                if y_offset > 620:
                    break
        else:
            self.draw_text("No items", self.body_font, GRAY, 70, y_offset)
        
        self.draw_text("Press ESC to return", self.small_font, LIGHT_GRAY, self.width // 2, 680, center=True)
    
    def update(self):
        pygame.display.flip()
        self.clock.tick(60)
    
    def quit(self):
        pygame.quit()
