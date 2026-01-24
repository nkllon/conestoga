"""
Pygame UI - Main game interface
Implements Requirements 1.3, 2.1, 10.2, 22.1-22.4
"""

import os
import pygame

from .events import EventDraft
from .state import GameState, ItemCatalog

# Retro Pixel Art Color Palette (inspired by classic Oregon Trail)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
OFF_WHITE = (240, 234, 214)

# Terrain colors
OCEAN_BLUE = (41, 128, 185)
PLAINS_GREEN = (118, 215, 96)
FOREST_GREEN = (34, 153, 84)
DESERT_TAN = (230, 176, 88)
MOUNTAIN_GRAY = (149, 165, 166)
RIVER_BLUE = (52, 152, 219)

# UI colors
BROWN = (139, 69, 19)
DARK_BROWN = (92, 64, 51)
TAN = (210, 180, 140)
GOLD = (255, 215, 0)
BRIGHT_YELLOW = (241, 196, 15)
ORANGE = (230, 126, 34)
RED = (231, 76, 60)
BRIGHT_RED = (192, 57, 43)
GREEN = (39, 174, 96)
BLUE = (52, 152, 219)
DARK_BLUE = (41, 128, 185)
PURPLE = (155, 89, 182)
GRAY = (149, 165, 166)
DARK_GRAY = (52, 73, 94)
LIGHT_GRAY = (189, 195, 199)


class GameUI:
    """Main UI controller for Conestoga"""

    def __init__(self, width: int = 1600, height: int = 1000):
        headless = os.environ.get("UI_HEADLESS", os.environ.get("CI", "0")) == "1"
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        self.width = width
        self.height = height
        flags = 0 if not headless else pygame.HIDDEN
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("CONESTOGA - The Oregon Trail Journey")

        # Pixel art style fonts (using default but with pixel-perfect sizing)
        self.title_font = pygame.font.Font(None, 64)
        self.heading_font = pygame.font.Font(None, 40)
        self.body_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font = pygame.font.Font(None, 20)

        self.clock = pygame.time.Clock()
        self.running = True

        # Pixel art cache for performance
        self.icon_cache = {}

        # Event log for displaying recent events
        self.event_log = []
        self.log_scroll_offset = 0  # Track scroll position

        # Gemini status (set by runner)
        self.gemini_online = True

        # Load Oregon Trail videos
        self.trail_videos = {
            "eastern_plains": "assets/conestoga loop - travel - eastern plains.mp4",
            "kansas_crossings": "assets/conestoga loop - travel - kansas crossings.mp4",
            "western_plains": "assets/conestoga loop - travel - western plains.mp4",
            "rocky_mountains": "assets/conestoga loop - travel - rocky mountains.mp4",
            "idaho_valley": "assets/conestoga loop - travel - idaho valley.mp4",
            "blue_mountains": "assets/conestoga loop - travel - blue mountains.mp4",
            "oregon_country": "assets/conestoga loop - travel - oregon.mp4",
        }
        
        # Trail segments with mile markers
        self.trail_segments = [
            {"name": "Eastern Plains", "video": "eastern_plains", "start_miles": 0, "end_miles": 250},
            {"name": "Kansas River", "video": "kansas_crossings", "start_miles": 250, "end_miles": 450},
            {"name": "Western Plains", "video": "western_plains", "start_miles": 450, "end_miles": 900},
            {"name": "Rocky Mountains", "video": "rocky_mountains", "start_miles": 900, "end_miles": 1300},
            {"name": "Idaho Valley", "video": "idaho_valley", "start_miles": 1300, "end_miles": 1600},
            {"name": "Blue Mountains", "video": "blue_mountains", "start_miles": 1600, "end_miles": 1850},
            {"name": "Oregon Country", "video": "oregon_country", "start_miles": 1850, "end_miles": 2000},
        ]
        
        # Video playback state
        self.current_video = None
        self.video_surface = None
        self.current_segment = "eastern_plains"
        self.video_playing = False  # Pause on first screen
        
        try:
            import cv2
            self.cv2 = cv2
            self.has_video = True
            print("[UI] Video support enabled (cv2 available)")
        except ImportError:
            self.has_video = False
            print("[UI] Video support disabled (cv2 not available)")
            # Fallback map
            try:
                self.map_image = pygame.image.load("assets/oregon_trail_map.png")
                print("[UI] Loaded fallback map image")
            except Exception as e:
                print(f"[UI] Failed to load fallback map: {e}")
                self.map_image = None

    def get_current_segment(self, miles: int) -> str:
        """Get the appropriate video segment based on miles traveled"""
        for segment in self.trail_segments:
            if segment["start_miles"] <= miles < segment["end_miles"]:
                return segment["video"]
        # Default to last segment if beyond range
        return self.trail_segments[-1]["video"]
    
    def load_video(self, segment_key: str):
        """Load a video for the current segment"""
        if not self.has_video:
            return
        
        video_path = self.trail_videos.get(segment_key)
        if not video_path or not os.path.exists(video_path):
            print(f"[UI] Video not found: {video_path}")
            return
        
        try:
            if self.current_video:
                self.current_video.release()
            self.current_video = self.cv2.VideoCapture(video_path)
            print(f"[UI] Loaded video: {segment_key}")
        except Exception as e:
            print(f"[UI] Failed to load video {segment_key}: {e}")
    
    def get_video_frame(self) -> pygame.Surface | None:
        """Get current frame from video, looping if needed"""
        if not self.has_video or not self.current_video:
            return None
        
        # Only advance frame if video is playing
        if self.video_playing:
            ret, frame = self.current_video.read()
            if not ret:
                # Loop video
                self.current_video.set(self.cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.current_video.read()
                if not ret:
                    return None
        else:
            # Paused - just read current frame without advancing
            ret, frame = self.current_video.read()
            if ret:
                # Rewind one frame to stay on current position
                current_pos = self.current_video.get(self.cv2.CAP_PROP_POS_FRAMES)
                self.current_video.set(self.cv2.CAP_PROP_POS_FRAMES, max(0, current_pos - 1))
            else:
                return None
        
        # Convert BGR to RGB and create pygame surface
        frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        frame = frame.swapaxes(0, 1)  # Transpose for pygame
        return pygame.surfarray.make_surface(frame)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return None
            elif event.type == pygame.KEYDOWN:
                return event.key
            elif event.type == pygame.MOUSEWHEEL:
                # Scroll event log with mouse wheel
                self.log_scroll_offset -= event.y  # y > 0 is scroll up, y < 0 is scroll down
                return None
        return None

    def draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple,
        x: int,
        y: int,
        center: bool = False,
        right: bool = False,
        max_width: int | None = None,
    ):
        if max_width:
            words = text.split(" ")
            lines = []
            current_line: list[str] = []

            for word in words:
                test_line = " ".join(current_line + [word])
                if font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))

            for i, line in enumerate(lines):
                surface = font.render(line, True, color)
                if center:
                    rect = surface.get_rect(center=(x, y + i * font.get_height()))
                elif right:
                    rect = surface.get_rect()
                    rect.right = x
                    rect.top = y + i * font.get_height()
                else:
                    rect = surface.get_rect(topleft=(x, y + i * font.get_height()))
                self.screen.blit(surface, rect)
            return len(lines) * font.get_height()
        else:
            surface = font.render(text, True, color)
            if center:
                rect = surface.get_rect(center=(x, y))
            elif right:
                rect = surface.get_rect()
                rect.right = x
                rect.top = y
            else:
                rect = surface.get_rect(topleft=(x, y))
            self.screen.blit(surface, rect)
            return font.get_height()

    def draw_panel(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple,
        border_color: tuple,
        thick: bool = False,
        padding: int = 0,
    ):
        """Draw panel with pixel art style borders"""
        # Main background
        pygame.draw.rect(self.screen, color, (x, y, width, height))

        # Pixel art style border (chunky retro look)
        border_width = 6 if thick else 4
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), border_width)

        # Inner highlight (3D effect)
        highlight_color = tuple(min(255, c + 30) for c in color)
        pygame.draw.line(
            self.screen,
            highlight_color,
            (x + border_width, y + border_width),
            (x + width - border_width, y + border_width),
            2,
        )
        pygame.draw.line(
            self.screen,
            highlight_color,
            (x + border_width, y + border_width),
            (x + border_width, y + height - border_width),
            2,
        )

        # Return inner content area coordinates if padding requested
        if padding:
            return (
                x + border_width + padding,
                y + border_width + padding,
                width - 2 * (border_width + padding),
                height - 2 * (border_width + padding),
            )

    def draw_pixel_icon(self, icon_type: str, x: int, y: int, size: int = 24):
        """Draw simple pixel art icons"""
        if icon_type == "wagon":
            # Wagon wheel and cover
            pygame.draw.rect(self.screen, DARK_BROWN, (x, y + size // 2, size, size // 2))
            pygame.draw.arc(self.screen, TAN, (x, y, size, size // 2), 0, 3.14, 3)
            pygame.draw.circle(self.screen, DARK_BROWN, (x + size // 4, y + size - 4), 5)
            pygame.draw.circle(self.screen, DARK_BROWN, (x + 3 * size // 4, y + size - 4), 5)
        elif icon_type == "food":
            # Bread loaf
            pygame.draw.ellipse(self.screen, TAN, (x, y + size // 3, size, 2 * size // 3))
            pygame.draw.rect(
                self.screen, DARK_BROWN, (x + size // 4, y + size // 2, size // 8, size // 4)
            )
        elif icon_type == "water":
            # Water droplet
            points = [
                (x + size // 2, y),
                (x + size, y + 2 * size // 3),
                (x + size // 2, y + size),
                (x, y + 2 * size // 3),
            ]
            pygame.draw.polygon(self.screen, RIVER_BLUE, points)
        elif icon_type == "ammo":
            # Bullet
            pygame.draw.rect(self.screen, GOLD, (x + size // 3, y, size // 3, 2 * size // 3))
            pygame.draw.circle(self.screen, GRAY, (x + size // 2, y + 2 * size // 3), size // 4)
        elif icon_type == "heart":
            # Health heart
            pygame.draw.circle(self.screen, RED, (x + size // 3, y + size // 3), size // 3)
            pygame.draw.circle(self.screen, RED, (x + 2 * size // 3, y + size // 3), size // 3)
            points = [(x, y + size // 3), (x + size // 2, y + size), (x + size, y + size // 3)]
            pygame.draw.polygon(self.screen, RED, points)
        elif icon_type == "mountain":
            # Mountain peak
            points = [(x + size // 2, y), (x + size, y + size), (x, y + size)]
            pygame.draw.polygon(self.screen, MOUNTAIN_GRAY, points)
            points = [
                (x + size // 2, y),
                (x + 3 * size // 4, y + size // 2),
                (x + size // 4, y + size // 2),
            ]
            pygame.draw.polygon(self.screen, WHITE, points)
        elif icon_type == "fort":
            # Fort building
            pygame.draw.rect(self.screen, DARK_BROWN, (x, y + size // 3, size, 2 * size // 3))
            pygame.draw.rect(
                self.screen, BLACK, (x + size // 3, y + size // 2, size // 3, size // 2)
            )
            points = [(x, y + size // 3), (x + size // 2, y), (x + size, y + size // 3)]
            pygame.draw.polygon(self.screen, BROWN, points)
        elif icon_type == "cloud":
            # Cloud (online/connected)
            # Cloud shape in green
            pygame.draw.circle(self.screen, GREEN, (x + size // 4, y + size // 2), size // 4)
            pygame.draw.circle(self.screen, GREEN, (x + size // 2, y + size // 3), size // 3)
            pygame.draw.circle(self.screen, GREEN, (x + 3 * size // 4, y + size // 2), size // 4)
            pygame.draw.rect(
                self.screen, GREEN, (x + size // 4, y + size // 2, size // 2, size // 4)
            )
            # Checkmark
            pygame.draw.line(
                self.screen,
                OFF_WHITE,
                (x + size // 3, y + size // 2),
                (x + 2 * size // 5, y + 2 * size // 3),
                2,
            )
            pygame.draw.line(
                self.screen,
                OFF_WHITE,
                (x + 2 * size // 5, y + 2 * size // 3),
                (x + 3 * size // 4, y + size // 3),
                2,
            )
        elif icon_type == "cloud_off":
            # Cloud with X (disconnected)
            # Cloud shape
            pygame.draw.circle(self.screen, GRAY, (x + size // 4, y + size // 2), size // 4)
            pygame.draw.circle(self.screen, GRAY, (x + size // 2, y + size // 3), size // 3)
            pygame.draw.circle(self.screen, GRAY, (x + 3 * size // 4, y + size // 2), size // 4)
            pygame.draw.rect(
                self.screen, GRAY, (x + size // 4, y + size // 2, size // 2, size // 4)
            )
            # Red X
            pygame.draw.line(
                self.screen,
                RED,
                (x + size // 3, y + size // 3),
                (x + 2 * size // 3, y + 2 * size // 3),
                3,
            )
            pygame.draw.line(
                self.screen,
                RED,
                (x + 2 * size // 3, y + size // 3),
                (x + size // 3, y + 2 * size // 3),
                3,
            )

    def add_to_log(self, message: str, category: str = "info", resources: dict = None, is_day_start: bool = False):
        """Add message to event log with optional resource changes"""
        self.event_log.append({"text": message, "category": category, "resources": resources or {}, "is_day_start": is_day_start})
        # Keep only last 50 messages (more room with scrolling)
        if len(self.event_log) > 50:
            self.event_log.pop(0)
        # Auto-scroll to bottom (most recent entry)
        self.log_scroll_offset = 0

    def draw_oregon_trail_map(self, game_state: GameState, x: int, y: int, width: int, height: int):
        """Draw Oregon Trail map using background image with wagon position overlay"""
        if self.map_image:
            # Scale and draw the map image
            scaled_map = pygame.transform.scale(self.map_image, (width, height))
            self.screen.blit(scaled_map, (x, y))

            # Calculate wagon position along the trail
            progress = min(1.0, game_state.miles_traveled / game_state.target_miles)

            # Trail coordinates (right to left, Independence to Oregon City)
            # WESTWARD TRAVEL = RIGHT TO LEFT
            trail_x_start = x + width * 0.88  # Independence, MO (EAST/RIGHT)
            trail_x_end = x + width * 0.08  # Oregon City (WEST/LEFT)
            trail_y_start = y + height * 0.47
            trail_y_end = y + height * 0.30

            wagon_x = int(trail_x_start + (trail_x_end - trail_x_start) * progress)
            wagon_y = int(trail_y_start + (trail_y_end - trail_y_start) * progress)

            # Draw wagon with shadow
            pygame.draw.ellipse(self.screen, (0, 0, 0, 100), (wagon_x - 20, wagon_y + 15, 40, 12))
            self.draw_pixel_icon("wagon", wagon_x - 20, wagon_y - 20, 40)
            return

        # Fallback: simple map if image not loaded
        """Draw detailed Oregon Trail map (westward - left to right)"""
        # Ocean background
        pygame.draw.rect(self.screen, OCEAN_BLUE, (x, y, width, height))

        # US landmass outline (simplified)
        # Northern border
        land_outline = [
            (x + 60, y + height * 0.25),  # Northeast coast
            (x + width * 0.3, y + height * 0.18),  # Great Lakes area
            (x + width * 0.5, y + height * 0.15),  # Northern plains
            (x + width * 0.75, y + height * 0.2),  # Northwest
            (x + width - 40, y + height * 0.28),  # Pacific Northwest
            # West coast
            (x + width - 40, y + height * 0.72),  # Oregon coast
            # Southern border
            (x + width * 0.8, y + height * 0.85),  # Southwest
            (x + width * 0.5, y + height * 0.88),  # Texas area
            (x + width * 0.25, y + height * 0.85),  # Southeast
            (x + 80, y + height * 0.75),  # East coast south
            (x + 60, y + height * 0.25),  # Back to start
        ]
        pygame.draw.polygon(self.screen, PLAINS_GREEN, land_outline)

        # Plains (eastern and central)
        for i in range(8):
            px = x + 60 + i * (width * 0.08)
            py = y + height * (0.35 + (i % 3) * 0.05)
            pw = width * 0.12
            ph = height * 0.35
            pygame.draw.rect(self.screen, PLAINS_GREEN, (px, py, pw, ph))

        # Desert (southwest)
        desert_points = [
            (x + width * 0.15, y + height * 0.7),
            (x + width * 0.45, y + height * 0.75),
            (x + width * 0.5, y + height * 0.88),
            (x + width * 0.2, y + height * 0.85),
        ]
        pygame.draw.polygon(self.screen, DESERT_TAN, desert_points)

        # Mountain range (Rockies - central)
        for i in range(7):
            mx = x + width * (0.42 + i * 0.05)
            my = y + height * (0.25 if i % 2 == 0 else 0.3)
            mw = 35 + (i % 3) * 8
            mh = 70 + (i % 2) * 15
            # Mountain body
            pygame.draw.polygon(
                self.screen, MOUNTAIN_GRAY, [(mx, my + mh), (mx + mw / 2, my), (mx + mw, my + mh)]
            )
            # Snow cap
            pygame.draw.polygon(
                self.screen,
                WHITE,
                [
                    (mx + mw / 2, my),
                    (mx + mw * 0.4, my + mh * 0.35),
                    (mx + mw * 0.6, my + mh * 0.35),
                ],
            )

        # Forest (Pacific Northwest)
        for i in range(6):
            fx = x + width * (0.75 + (i % 3) * 0.05)
            fy = y + height * (0.28 + (i // 3) * 0.15)
            fw = width * 0.08
            fh = height * 0.18
            pygame.draw.rect(self.screen, FOREST_GREEN, (fx, fy, fw, fh))

        # Rivers
        # Missouri River
        pygame.draw.line(
            self.screen,
            RIVER_BLUE,
            (x + width * 0.2, y + height * 0.3),
            (x + width * 0.28, y + height * 0.5),
            6,
        )
        # Platte River
        pygame.draw.line(
            self.screen,
            RIVER_BLUE,
            (x + width * 0.28, y + height * 0.48),
            (x + width * 0.45, y + height * 0.46),
            5,
        )
        # Snake/Columbia Rivers
        pygame.draw.line(
            self.screen,
            RIVER_BLUE,
            (x + width * 0.7, y + height * 0.35),
            (x + width * 0.88, y + height * 0.48),
            6,
        )

        # The Oregon Trail (empty - westward from Missouri to Oregon)
        trail_segments = [
            (x + width * 0.25, y + height * 0.52),  # Independence, Missouri
            (x + width * 0.32, y + height * 0.51),  # Kansas plains
            (x + width * 0.38, y + height * 0.49),  # Fort Kearny
            (x + width * 0.45, y + height * 0.47),  # Platte River
            (x + width * 0.52, y + height * 0.43),  # Chimney Rock
            (x + width * 0.57, y + height * 0.41),  # Fort Laramie
            (x + width * 0.63, y + height * 0.39),  # Independence Rock
            (x + width * 0.68, y + height * 0.38),  # South Pass
            (x + width * 0.73, y + height * 0.42),  # Fort Bridger
            (x + width * 0.78, y + height * 0.45),  # Snake River
            (x + width * 0.85, y + height * 0.47),  # Blue Mountains
            (x + width * 0.92, y + height * 0.49),  # Oregon City!
        ]

        # Draw the trail path progressively based on game progress
        progress_ratio = min(1.0, game_state.miles_traveled / game_state.target_miles)
        total_segments = len(trail_segments) - 1
        completed_segments = int(progress_ratio * total_segments)

        # Completed trail segments (brown path)
        for i in range(completed_segments):
            pygame.draw.line(self.screen, DARK_BROWN, trail_segments[i], trail_segments[i + 1], 8)
            # Add dotted sides to trail
            pygame.draw.line(
                self.screen,
                TAN,
                (trail_segments[i][0] - 3, trail_segments[i][1] - 3),
                (trail_segments[i + 1][0] - 3, trail_segments[i + 1][1] - 3),
                2,
            )
            pygame.draw.line(
                self.screen,
                TAN,
                (trail_segments[i][0] + 3, trail_segments[i][1] + 3),
                (trail_segments[i + 1][0] + 3, trail_segments[i + 1][1] + 3),
                2,
            )

        # Partial current segment
        if completed_segments < total_segments:
            segment_progress = (progress_ratio * total_segments) - completed_segments
            start = trail_segments[completed_segments]
            end = trail_segments[completed_segments + 1]
            partial_x = start[0] + (end[0] - start[0]) * segment_progress
            partial_y = start[1] + (end[1] - start[1]) * segment_progress
            pygame.draw.line(self.screen, DARK_BROWN, start, (partial_x, partial_y), 8)

        # Draw the Oregon Trail (brown path from left/east to right/west)
        trail_points = [
            (x + 60, y + height * 0.5),  # Start (Missouri/Independence)
            (x + width * 0.15, y + height * 0.48),
            (x + width * 0.25, y + height * 0.52),  # Fort Kearny area
            (x + width * 0.35, y + height * 0.45),  # Cross river
            (x + width * 0.42, y + height * 0.38),  # Chimney Rock
            (x + width * 0.5, y + height * 0.35),  # Fort Laramie
            (x + width * 0.58, y + height * 0.32),  # Mountains start
            (x + width * 0.66, y + height * 0.36),  # Independence Rock
            (x + width * 0.74, y + height * 0.42),  # South Pass
            (x + width * 0.82, y + height * 0.45),  # Fort Bridger
            (x + width * 0.9, y + height * 0.48),  # Near Oregon
            (x + width - 40, y + height * 0.5),  # Oregon City!
        ]

        # Draw trail segments based on progress
        progress_ratio = min(1.0, game_state.miles_traveled / game_state.target_miles)
        total_segments = len(trail_points) - 1
        completed_segments = int(progress_ratio * total_segments)

        # Draw completed trail segments
        for i in range(completed_segments):
            pygame.draw.line(self.screen, DARK_BROWN, trail_points[i], trail_points[i + 1], 6)

        # Draw partial current segment
        if completed_segments < total_segments:
            segment_progress = (progress_ratio * total_segments) - completed_segments
            start = trail_points[completed_segments]
            end = trail_points[completed_segments + 1]
            partial_x = start[0] + (end[0] - start[0]) * segment_progress
            partial_y = start[1] + (end[1] - start[1]) * segment_progress
            pygame.draw.line(self.screen, DARK_BROWN, start, (partial_x, partial_y), 6)

        # Draw landmarks on trail
        landmarks = [
            (0.0, "Independence", "Start", (x + 60, y + height * 0.5)),
            (0.15, "Fort Kearny", "fort", (x + width * 0.25, y + height * 0.52)),
            (0.35, "Chimney Rock", "mountain", (x + width * 0.42, y + height * 0.38)),
            (0.50, "Fort Laramie", "fort", (x + width * 0.5, y + height * 0.35)),
            (0.65, "Independence Rock", "mountain", (x + width * 0.66, y + height * 0.36)),
            (0.82, "Fort Bridger", "fort", (x + width * 0.82, y + height * 0.45)),
            (1.0, "Oregon City", "End", (x + width - 40, y + height * 0.5)),
        ]

        for pos, name, icon_type, (lx, ly) in landmarks:
            if pos <= progress_ratio + 0.05:  # Show slightly ahead
                # Draw icon
                if icon_type == "fort":
                    self.draw_pixel_icon(icon_type, int(lx - 12), int(ly - 32), 24)
                elif icon_type == "mountain":
                    self.draw_pixel_icon(icon_type, int(lx - 12), int(ly - 32), 24)
                elif icon_type == "Start":
                    # Draw start flag
                    pygame.draw.rect(self.screen, DARK_BROWN, (int(lx - 2), int(ly - 30), 4, 30))
                    pygame.draw.polygon(
                        self.screen,
                        GREEN,
                        [
                            (int(lx), int(ly - 30)),
                            (int(lx + 20), int(ly - 22)),
                            (int(lx), int(ly - 14)),
                        ],
                    )
                elif icon_type == "End":
                    # Draw end flag
                    pygame.draw.rect(self.screen, DARK_BROWN, (int(lx - 2), int(ly - 30), 4, 30))
                    pygame.draw.polygon(
                        self.screen,
                        GOLD,
                        [
                            (int(lx), int(ly - 30)),
                            (int(lx + 20), int(ly - 22)),
                            (int(lx), int(ly - 14)),
                        ],
                    )

                # Draw label with background
                label_w = self.tiny_font.size(name)[0] + 8
                label_h = 18
                pygame.draw.rect(
                    self.screen, BLACK, (int(lx - label_w // 2), int(ly - 48), label_w, label_h)
                )
                pygame.draw.rect(
                    self.screen,
                    GOLD,
                    (int(lx - label_w // 2), int(ly - 48), label_w, label_h),
                    2,
                )
                self.draw_text(name, self.tiny_font, OFF_WHITE, int(lx), int(ly - 38), center=True)

        # Draw wagon at current position
        wagon_idx = min(int(progress_ratio * (len(trail_points) - 1)), len(trail_points) - 2)
        wagon_segment_progress = (progress_ratio * (len(trail_points) - 1)) - wagon_idx
        wagon_start = trail_points[wagon_idx]
        wagon_end = trail_points[wagon_idx + 1]
        wagon_x = wagon_start[0] + (wagon_end[0] - wagon_start[0]) * wagon_segment_progress
        wagon_y = wagon_start[1] + (wagon_end[1] - wagon_start[1]) * wagon_segment_progress

        # Draw wagon with shadow
        pygame.draw.ellipse(
            self.screen, (0, 0, 0, 100), (int(wagon_x - 20), int(wagon_y + 15), 40, 12)
        )
        self.draw_pixel_icon("wagon", int(wagon_x - 20), int(wagon_y - 20), 40)

    def render_travel_screen(self, game_state: GameState):
        # Background - sky
        self.screen.fill(OCEAN_BLUE)
        
        # Start video playing after day 2
        if game_state.day >= 2 and not self.video_playing:
            self.video_playing = True
        
        # Check if we need to change video segment
        new_segment = self.get_current_segment(game_state.miles_traveled)
        if new_segment != self.current_segment:
            self.current_segment = new_segment
            self.load_video(new_segment)
        
        # If no video loaded yet, load the starting one
        if self.has_video and not self.current_video:
            self.load_video(self.current_segment)
        
        # === VIDEO/MAP AREA (Top portion) ===
        video_height = int(self.height * 0.65)  # 65% for video
        timeline_height = 80  # Timeline between video and bottom panels
        
        # Calculate video dimensions maintaining aspect ratio (1664x1244 = 1.34:1)
        max_video_height = video_height - 100  # Leave room for title
        video_display_width = int(max_video_height * 1.34)
        video_display_height = max_video_height
        
        # Video panel sized to fit video
        video_panel_width = video_display_width + 40
        self.draw_panel(
            15, 15, video_panel_width, video_height, BLACK, DARK_BROWN, thick=True, padding=5
        )
        
        # Title at top (centered vertically in the title area)
        self.draw_text(
            "CONESTOGA - Oregon Trail",
            self.title_font,
            BRIGHT_YELLOW,
            video_panel_width // 2,
            45,  # Centered in ~70px title area
            center=True,
        )
        
        # Video playback area
        video_area_y = 80
        
        if self.has_video:
            # Get and display current video frame
            frame = self.get_video_frame()
            if frame:
                # Scale frame maintaining aspect ratio, left aligned
                scaled_frame = pygame.transform.scale(frame, (video_display_width, video_display_height))
                self.screen.blit(scaled_frame, (30, video_area_y))
            else:
                # Fallback: solid color with text
                pygame.draw.rect(self.screen, DARK_GRAY, (30, video_area_y, video_display_width, video_display_height))
                self.draw_text(
                    f"Traveling through {self.current_segment.replace('_', ' ').title()}",
                    self.heading_font,
                    OFF_WHITE,
                    video_panel_width // 2,
                    video_area_y + video_display_height // 2,
                    center=True,
                )
        else:
            # Fallback: use map image or solid color
            if self.map_image:
                scaled_map = pygame.transform.scale(self.map_image, (video_display_width, video_display_height))
                self.screen.blit(scaled_map, (30, video_area_y))
            else:
                pygame.draw.rect(self.screen, PLAINS_GREEN, (30, video_area_y, video_display_width, video_display_height))
                self.draw_text(
                    "Oregon Trail",
                    self.heading_font,
                    DARK_BROWN,
                    video_panel_width // 2,
                    video_area_y + video_display_height // 2,
                    center=True,
                )

        # === TIMELINE (Below video) ===
        timeline_y = video_height + 20
        
        # Timeline panel
        self.draw_panel(15, timeline_y, video_panel_width, timeline_height, BLACK, DARK_BROWN, thick=True, padding=5)
        
        # Calculate centered timeline bar dimensions
        timeline_bar_width = 700  # Expanded width for better segment uniformity
        timeline_start_x = 15 + (video_panel_width - timeline_bar_width) // 2
        
        # Vertically center the timeline content within the panel with padding
        content_height = 60  # Total height: day info + bar + labels
        bar_y = timeline_y + (timeline_height - content_height) // 2 + 18  # Offset for day info above
        bar_height = 12
        pygame.draw.rect(self.screen, DARK_GRAY, (timeline_start_x, bar_y, timeline_bar_width, bar_height))
        
        # Draw segment markers and labels
        total_miles = game_state.target_miles
        progress = game_state.miles_traveled / total_miles
        
        for i, segment in enumerate(self.trail_segments):
            # Calculate position
            seg_start = segment["start_miles"] / total_miles
            seg_end = segment["end_miles"] / total_miles
            seg_x = timeline_start_x + int(seg_start * timeline_bar_width)
            seg_width = int((seg_end - seg_start) * timeline_bar_width)
            
            # Highlight current segment
            is_current = (game_state.miles_traveled >= segment["start_miles"] and 
                         game_state.miles_traveled < segment["end_miles"])
            color = BRIGHT_YELLOW if is_current else GRAY
            
            # Draw segment bar
            pygame.draw.rect(self.screen, color, (seg_x, bar_y, seg_width, bar_height), 2)
            
            # Segment label - stack words vertically, centered
            words = segment["name"].split()
            label_x = seg_x + seg_width // 2
            label_y = bar_y + 20  # Start below the bar with padding
            
            for word in words:
                self.draw_text(
                    word,
                    self.tiny_font,
                    color,
                    label_x,
                    label_y,
                    center=True
                )
                label_y += 12  # Stack next word below
        
        # Draw wagon icon at current position
        wagon_x = timeline_start_x + int(progress * timeline_bar_width)
        wagon_y = bar_y + bar_height // 2
        pygame.draw.circle(self.screen, BROWN, (wagon_x, wagon_y), 8)
        pygame.draw.circle(self.screen, OFF_WHITE, (wagon_x, wagon_y), 6)
        
        # Overlay: Day and Distance (above the bar)
        overlay_y = bar_y - 18
        self.draw_text(
            f"Day {game_state.day}",
            self.small_font,
            BRIGHT_YELLOW,
            timeline_start_x,
            overlay_y
        )
        
        miles_pct = min(100, int(100 * game_state.miles_traveled / total_miles))
        self.draw_text(
            f"{game_state.miles_traveled} / {total_miles} miles ({miles_pct}%)",
            self.small_font,
            BRIGHT_YELLOW,
            timeline_start_x + timeline_bar_width,
            overlay_y,
            right=True
        )

        # === EVENT LOG (Right side) - extends to fill remaining space ===
        log_x = video_panel_width + 25
        log_width = self.width - log_x - 15
        event_log_height = video_height + timeline_height + 25

        self.draw_panel(log_x, 15, log_width, event_log_height, BLACK, GOLD, thick=True)
        self.draw_text("Event Log", self.heading_font, BRIGHT_YELLOW, log_x + 20, 30)

        # Draw Gemini status indicator in event log header
        status_x = log_x + log_width - 90
        status_y = 25
        if self.gemini_online:
            self.draw_pixel_icon("cloud", status_x, status_y, 24)
            self.draw_text("AI ON", self.tiny_font, GREEN, status_x + 30, status_y + 5)
        else:
            self.draw_pixel_icon("cloud_off", status_x, status_y, 24)
            self.draw_text("AI OFF", self.tiny_font, RED, status_x + 30, status_y + 5)

        # Draw log entries with scrolling (no truncation, more entries)
        log_y = 70
        max_visible = 25  # Increased from 15
        total_logs = len(self.event_log)

        # Clamp scroll offset (0 = newest entries visible)
        max_scroll = max(0, total_logs - max_visible)
        self.log_scroll_offset = max(0, min(self.log_scroll_offset, max_scroll))

        # Calculate visible slice
        if total_logs <= max_visible:
            # Show all entries if we have fewer than max_visible
            visible_logs = self.event_log
        else:
            # When offset=0, show the LAST max_visible entries (newest at bottom)
            # When offset increases, scroll back to show older entries
            start_idx = max(0, total_logs - max_visible - self.log_scroll_offset)
            end_idx = total_logs - self.log_scroll_offset
            visible_logs = self.event_log[start_idx:end_idx]

        for entry in visible_logs:
            # Add visual separator for new day
            if entry.get("is_day_start", False):
                # Draw horizontal line separator
                separator_y = log_y - 5
                pygame.draw.line(
                    self.screen, GRAY, 
                    (log_x + 20, separator_y), 
                    (log_x + log_width - 20, separator_y), 
                    1
                )
                log_y += 10
            
            color = OFF_WHITE
            if entry["category"] == "warning":
                color = ORANGE
            elif entry["category"] == "danger":
                color = RED
            elif entry["category"] == "success":
                color = GREEN

            # Draw text with word wrapping
            text = entry["text"]
            lines_height = self.draw_text(text, self.tiny_font, color, log_x + 20, log_y, max_width=log_width - 40)
            log_y += lines_height + 4
            
            # Draw resource changes if present
            resources = entry.get("resources", {})
            if resources:
                resource_y = log_y
                resource_x = log_x + 40
                
                # Display each resource change with icon
                for resource, change in resources.items():
                    if change == 0:
                        continue
                    
                    # Draw icon
                    icon_name = resource.lower()
                    self.draw_pixel_icon(icon_name, resource_x, resource_y - 2, 16)
                    
                    # Draw change amount
                    change_color = GREEN if change > 0 else RED
                    change_text = f"{'+' if change > 0 else ''}{change}"
                    self.draw_text(change_text, self.tiny_font, change_color, resource_x + 20, resource_y)
                    
                    resource_x += 80  # Space between resource indicators
                
                log_y += 22
            
            log_y += 3  # Small spacing between entries
            if log_y > event_log_height - 40:
                break

        # Scroll instructions at bottom
        scroll_y = event_log_height - 10
        scroll_text = "UP/DN or wheel to scroll"
        self.draw_text(
            scroll_text, self.tiny_font, GRAY, log_x + log_width // 2, scroll_y, center=True
        )

        # === BOTTOM PANEL (Party & Resources) ===
        bottom_y = video_height + timeline_height + 30
        bottom_height = 190  # Fixed height to fit content

        # Left: Resources
        res_width = 480
        self.draw_panel(15, bottom_y, res_width, bottom_height, DARK_GRAY, GOLD, thick=True)
        self.draw_text("Resources", self.body_font, BRIGHT_YELLOW, 35, bottom_y + 10)

        # Resources with consistent spacing
        y = bottom_y + 50
        col1_icon_x = 35
        col1_text_x = 68
        col2_icon_x = 260
        col2_text_x = 293

        # Row 1: Food and Water
        self.draw_pixel_icon("food", col1_icon_x, y, 24)
        self.draw_text(
            f"Food: {game_state.food} lbs", self.small_font, OFF_WHITE, col1_text_x, y + 2
        )

        self.draw_pixel_icon("water", col2_icon_x, y, 24)
        self.draw_text(f"Water: {game_state.water}", self.small_font, OFF_WHITE, col2_text_x, y + 2)

        # Row 2: Ammo and Money
        y += 40
        self.draw_pixel_icon("ammo", col1_icon_x, y, 24)
        self.draw_text(f"Ammo: {game_state.ammo}", self.small_font, OFF_WHITE, col1_text_x, y + 2)

        # Money icon (coin)
        pygame.draw.circle(self.screen, GOLD, (col2_icon_x + 12, y + 12), 10)
        pygame.draw.circle(self.screen, DARK_BROWN, (col2_icon_x + 12, y + 12), 8)
        self.draw_text("$", self.tiny_font, GOLD, col2_icon_x + 12, y + 12, center=True)
        self.draw_text(f"{game_state.money}", self.small_font, GOLD, col2_text_x, y + 2)

        # Row 3: Wagon
        y += 40
        wagon_color = (
            GREEN
            if game_state.wagon_health > 50
            else (ORANGE if game_state.wagon_health > 25 else RED)
        )
        self.draw_pixel_icon("wagon", col1_icon_x, y - 4, 28)
        self.draw_text(
            f"Wagon: {game_state.wagon_health}%", self.small_font, wagon_color, col1_text_x, y + 2
        )

        # Middle: Party
        party_x = res_width + 25
        party_width = 650
        self.draw_panel(party_x, bottom_y, party_width, bottom_height, DARK_GRAY, GOLD, thick=True)
        self.draw_text("Party Status", self.body_font, BRIGHT_YELLOW, party_x + 20, bottom_y + 10)

        y = bottom_y + 50
        for member in game_state.party:
            health_color = GREEN if member.health > 50 else (ORANGE if member.health > 20 else RED)

            # Name and health
            self.draw_pixel_icon("heart", party_x + 20, y, 20)
            self.draw_text(f"{member.name}", self.small_font, OFF_WHITE, party_x + 50, y + 2)

            # Health bar
            bar_x = party_x + 180
            bar_w = 180
            bar_h = 16
            pygame.draw.rect(self.screen, BLACK, (bar_x, y + 3, bar_w, bar_h), 2)
            filled = int(bar_w * member.health / 100)
            if filled > 0:
                pygame.draw.rect(
                    self.screen, health_color, (bar_x + 2, y + 5, filled - 4, bar_h - 4)
                )

            # Health %
            self.draw_text(
                f"{member.health}%", self.tiny_font, health_color, bar_x + bar_w + 8, y + 4
            )

            # Status
            if member.status_conditions:
                status = ", ".join(member.status_conditions[:2])
                self.draw_text(f"[{status}]", self.tiny_font, RED, party_x + 450, y + 4)

            y += 35

        # Right: Controls
        ctrl_x = party_x + party_width + 10
        ctrl_width = self.width - ctrl_x - 15
        self.draw_panel(ctrl_x, bottom_y, ctrl_width, bottom_height, BLACK, GOLD, thick=True)
        self.draw_text(
            "Controls",
            self.body_font,
            BRIGHT_YELLOW,
            ctrl_x + ctrl_width // 2,
            bottom_y + 18,
            center=True,
        )

        # Horizontal layout - all controls in one row, evenly spaced and centered
        y = bottom_y + 70
        padding = 20
        available_width = ctrl_width - 2 * padding
        col_width = available_width // 3

        col1_center = ctrl_x + padding + col_width // 2
        col2_center = ctrl_x + padding + col_width + col_width // 2
        col3_center = ctrl_x + padding + 2 * col_width + col_width // 2

        # SPACE - Travel
        self.draw_text("[SPACE]", self.small_font, BRIGHT_YELLOW, col1_center, y, center=True)
        self.draw_text("Travel", self.tiny_font, OFF_WHITE, col1_center, y + 25, center=True)

        # I - Inventory
        self.draw_text("[I]", self.small_font, BRIGHT_YELLOW, col2_center, y, center=True)
        self.draw_text("Inventory", self.tiny_font, OFF_WHITE, col2_center, y + 25, center=True)

        # Q - Quit
        self.draw_text("[Q]", self.small_font, BRIGHT_YELLOW, col3_center, y, center=True)
        self.draw_text("Quit", self.tiny_font, OFF_WHITE, col3_center, y + 25, center=True)

    def render_event_screen(
        self, event: EventDraft, game_state: GameState, selected_choice: int = 0
    ):
        # Start video playback after first event
        self.video_playing = True
        
        # Dramatic dark background
        self.screen.fill(DARK_GRAY)

        # Calculate vertical centering for event content
        total_height = 60 + 200 + 20 + 60 + 20 + (len(event.choices) * 80)
        start_y = (self.height - 250 - total_height) // 2  # Account for bottom panel space
        
        # Event title banner (no "*** EVENT ***" text)
        title_y = start_y
        self.draw_panel(self.width // 2 - 400, title_y, 800, 60, DARK_BROWN, BRIGHT_RED, thick=True)
        self.draw_text(event.title, self.title_font, OFF_WHITE, self.width // 2, title_y + 25, center=True)

        # Narrative panel
        narrative_y = title_y + 80
        self.draw_panel(40, narrative_y, self.width - 80, 200, BLACK, ORANGE, thick=True)
        self.draw_text(
            event.narrative, self.body_font, OFF_WHITE, 70, narrative_y + 25, max_width=self.width - 140
        )

        # Choices header
        choices_header_y = narrative_y + 220
        self.draw_panel(40, choices_header_y, self.width - 80, 60, DARK_BLUE, BRIGHT_YELLOW)
        self.draw_text("Choose Your Action:", self.heading_font, OFF_WHITE, 60, choices_header_y + 15)

        # Choices - use two columns if more than 3 choices
        num_choices = len(event.choices)
        use_two_columns = num_choices > 3
        
        y_offset = choices_header_y + 80
        
        if use_two_columns:
            # Two column layout
            choices_per_column = (num_choices + 1) // 2  # Round up
            col_width = (self.width - 80 - 30) // 2  # Subtract margins and gap
            choice_height = 70
            
            for i, choice in enumerate(event.choices):
                is_available = choice.is_available(game_state)
                is_selected = i == selected_choice
                
                # Calculate position
                col = i // choices_per_column
                row = i % choices_per_column
                x_pos = 40 + col * (col_width + 30)
                y_pos = y_offset + row * (choice_height + 12)

                # Choice button styling
                if not is_available:
                    bg_color = GRAY
                    border_color = DARK_GRAY
                elif is_selected:
                    bg_color = ORANGE
                    border_color = BRIGHT_YELLOW
                else:
                    bg_color = DARK_BROWN
                    border_color = TAN

                self.draw_panel(
                    x_pos,
                    y_pos,
                    col_width,
                    choice_height,
                    bg_color,
                    border_color,
                    thick=is_selected,
                )

                # Choice number badge
                badge_size = 40
                badge_x = x_pos + 15
                badge_y = y_pos + 15
                pygame.draw.circle(
                    self.screen,
                    border_color,
                    (badge_x + badge_size // 2, badge_y + badge_size // 2),
                    badge_size // 2,
                )
                pygame.draw.circle(
                    self.screen,
                    bg_color if is_selected else BLACK,
                    (badge_x + badge_size // 2, badge_y + badge_size // 2),
                    badge_size // 2 - 4,
                )
                self.draw_text(
                    str(i + 1),
                    self.heading_font,
                    border_color,
                    badge_x + badge_size // 2,
                    badge_y + badge_size // 2 + 2,
                    center=True,
                )

                # Choice text
                choice_text = choice.text
                text_color = OFF_WHITE if is_available else DARK_GRAY
                self.draw_text(
                    choice_text,
                    self.body_font,
                    text_color,
                    x_pos + 75,
                    y_pos + 15,
                    max_width=col_width - 95,
                )

                # Lock reason
                if not is_available:
                    lock_reason = choice.get_lock_reason(game_state)
                    if lock_reason:
                        self.draw_text(
                            f"🔒 {lock_reason}", self.small_font, BRIGHT_RED, x_pos + 75, y_pos + 45
                        )
            
            # Update y_offset for controls hint
            y_offset = y_offset + choices_per_column * (choice_height + 12)
        else:
            # Single column layout (original)
            for i, choice in enumerate(event.choices):
                is_available = choice.is_available(game_state)
                is_selected = i == selected_choice

                choice_height = 70

                # Choice button styling
                if not is_available:
                    bg_color = GRAY
                    border_color = DARK_GRAY
                elif is_selected:
                    bg_color = ORANGE
                    border_color = BRIGHT_YELLOW
                else:
                    bg_color = DARK_BROWN
                    border_color = TAN

                self.draw_panel(
                    40,
                    y_offset,
                    self.width - 80,
                    choice_height,
                    bg_color,
                    border_color,
                    thick=is_selected,
                )

                # Choice number badge
                badge_size = 40
                badge_x = 55
                badge_y = y_offset + 15
                pygame.draw.circle(
                    self.screen,
                    border_color,
                    (badge_x + badge_size // 2, badge_y + badge_size // 2),
                    badge_size // 2,
                )
                pygame.draw.circle(
                    self.screen,
                    bg_color if is_selected else BLACK,
                    (badge_x + badge_size // 2, badge_y + badge_size // 2),
                    badge_size // 2 - 4,
                )
                self.draw_text(
                    str(i + 1),
                    self.heading_font,
                    border_color,
                    badge_x + badge_size // 2,
                    badge_y + badge_size // 2 + 2,
                    center=True,
                )

                # Choice text
                choice_text = choice.text
                text_color = OFF_WHITE if is_available else DARK_GRAY
                self.draw_text(
                    choice_text,
                    self.body_font,
                    text_color,
                    115,
                    y_offset + 15,
                    max_width=self.width - 180,
                )

                # Lock reason
                if not is_available:
                    lock_reason = choice.get_lock_reason(game_state)
                    if lock_reason:
                        self.draw_text(
                            f"🔒 {lock_reason}", self.small_font, BRIGHT_RED, 115, y_offset + 45
                        )

                y_offset += choice_height + 12

        # Controls hint
        y_offset += 10
        self.draw_text(
            "[UP/DOWN] Navigate  |  [ENTER] Confirm",
            self.body_font,
            LIGHT_GRAY,
            self.width // 2,
            y_offset,
            center=True,
        )

        # === BOTTOM PANELS (Party, Resources, Controls) ===
        bottom_y = self.height - 200
        bottom_height = 190

        # Left: Resources
        res_width = 480
        self.draw_panel(15, bottom_y, res_width, bottom_height, DARK_GRAY, GOLD, thick=True)
        self.draw_text("Resources", self.body_font, BRIGHT_YELLOW, 35, bottom_y + 10)

        # Resources with consistent spacing
        y = bottom_y + 50
        col1_icon_x = 35
        col1_text_x = 68
        col2_icon_x = 260
        col2_text_x = 293

        # Row 1: Food and Water
        self.draw_pixel_icon("food", col1_icon_x, y, 24)
        self.draw_text(
            f"Food: {game_state.food} lbs", self.small_font, OFF_WHITE, col1_text_x, y + 2
        )
        self.draw_pixel_icon("water", col2_icon_x, y, 24)
        self.draw_text(
            f"Water: {game_state.water} gal", self.small_font, OFF_WHITE, col2_text_x, y + 2
        )

        # Row 2: Ammo and Money
        y += 40
        self.draw_pixel_icon("ammo", col1_icon_x, y, 24)
        self.draw_text(f"Ammo: {game_state.ammo}", self.small_font, OFF_WHITE, col1_text_x, y + 2)
        pygame.draw.circle(self.screen, GOLD, (col2_icon_x + 12, y + 12), 10)
        pygame.draw.circle(self.screen, DARK_BROWN, (col2_icon_x + 12, y + 12), 8)
        self.draw_text("$", self.tiny_font, GOLD, col2_icon_x + 12, y + 12, center=True)
        self.draw_text(f"{game_state.money}", self.small_font, GOLD, col2_text_x, y + 2)

        # Row 3: Wagon
        y += 40
        wagon_color = (
            GREEN
            if game_state.wagon_health > 50
            else (ORANGE if game_state.wagon_health > 25 else RED)
        )
        self.draw_pixel_icon("wagon", col1_icon_x, y - 4, 28)
        self.draw_text(
            f"Wagon: {game_state.wagon_health}%", self.small_font, wagon_color, col1_text_x, y + 2
        )

        # Middle: Party
        party_x = res_width + 25
        party_width = 650
        self.draw_panel(party_x, bottom_y, party_width, bottom_height, DARK_GRAY, GOLD, thick=True)
        self.draw_text("Party Status", self.body_font, BRIGHT_YELLOW, party_x + 20, bottom_y + 10)

        y = bottom_y + 50
        for member in game_state.party:
            health_color = GREEN if member.health > 50 else (ORANGE if member.health > 20 else RED)

            # Name and health
            self.draw_pixel_icon("heart", party_x + 20, y, 20)
            self.draw_text(f"{member.name}", self.small_font, OFF_WHITE, party_x + 50, y + 2)

            # Health bar
            bar_x = party_x + 180
            bar_w = 180
            bar_h = 16
            pygame.draw.rect(self.screen, BLACK, (bar_x, y + 3, bar_w, bar_h), 2)
            filled = int(bar_w * member.health / 100)
            if filled > 0:
                pygame.draw.rect(
                    self.screen, health_color, (bar_x + 2, y + 5, filled - 4, bar_h - 4)
                )

            # Health %
            self.draw_text(
                f"{member.health}%", self.tiny_font, health_color, bar_x + bar_w + 8, y + 4
            )

            # Status
            if member.status_conditions:
                status = ", ".join(member.status_conditions[:2])
                self.draw_text(f"[{status}]", self.tiny_font, RED, party_x + 450, y + 4)

            y += 35

        # Right: Controls (empty placeholder)
        ctrl_x = party_x + party_width + 10
        ctrl_width = self.width - ctrl_x - 15
        self.draw_panel(ctrl_x, bottom_y, ctrl_width, bottom_height, BLACK, GOLD, thick=True)

    def render_loading_screen(self, elapsed_time: float):
        """Req 10.2: Lightweight loading state during async event generation"""
        # Prairie sunset background
        self.screen.fill(DARK_BLUE)
        pygame.draw.rect(self.screen, ORANGE, (0, self.height // 2, self.width, self.height // 2))

        # Loading banner
        self.draw_panel(self.width // 2 - 350, 150, 700, 120, DARK_BROWN, BRIGHT_YELLOW, thick=True)
        self.draw_text(
            "🎲 Generating Event...",
            self.title_font,
            BRIGHT_YELLOW,
            self.width // 2,
            180,
            center=True,
        )

        # Animated loading text
        dots = "." * (int(elapsed_time * 2) % 4) + " " * (3 - int(elapsed_time * 2) % 4)
        loading_text = f"Gemini 3 AI at work{dots}"
        self.draw_text(
            loading_text, self.heading_font, OFF_WHITE, self.width // 2, 235, center=True
        )

        # Animated wagon train
        wagon_x = (int(elapsed_time * 100) % (self.width + 200)) - 100
        wagon_y = 350

        # Draw multiple wagons
        for i in range(3):
            wx = wagon_x - i * 150
            if 0 <= wx <= self.width:
                self.draw_pixel_icon("wagon", wx, wagon_y, 48)

        # Progress indicator
        elapsed_display = f"⏱️ {elapsed_time:.1f}s"
        self.draw_text(
            elapsed_display, self.body_font, LIGHT_GRAY, self.width // 2, 450, center=True
        )

        # Spinning compass/wheel
        wheel_center = (self.width // 2, 550)
        wheel_radius = 50
        angle = (elapsed_time * 180) % 360

        # Outer ring
        pygame.draw.circle(self.screen, DARK_BROWN, wheel_center, wheel_radius, 6)

        # Spokes
        for i in range(8):
            spoke_angle = (angle + i * 45) * 3.14159 / 180
            end_x = wheel_center[0] + int(
                wheel_radius * pygame.math.Vector2(1, 0).rotate(spoke_angle * 180 / 3.14159).x
            )
            end_y = wheel_center[1] + int(
                wheel_radius * pygame.math.Vector2(1, 0).rotate(spoke_angle * 180 / 3.14159).y
            )
            pygame.draw.line(self.screen, TAN, wheel_center, (end_x, end_y), 4)

        # Center hub
        pygame.draw.circle(self.screen, DARK_BROWN, wheel_center, 12)
        pygame.draw.circle(self.screen, GOLD, wheel_center, 8)

        # Hint (Req 10.5)
        self.draw_text(
            "[ESC] Use Fallback Event",
            self.body_font,
            LIGHT_GRAY,
            self.width // 2,
            650,
            center=True,
        )

    def render_resolution_screen(self, resolution_text: str):
        # Parchment-style background
        self.screen.fill(DARK_GRAY)

        # Outcome banner
        self.draw_panel(self.width // 2 - 300, 30, 600, 90, DARK_BROWN, GOLD, thick=True)
        self.draw_text(
            "*** OUTCOME ***", self.title_font, BRIGHT_YELLOW, self.width // 2, 75, center=True
        )

        # Story panel (parchment style)
        self.draw_panel(80, 150, self.width - 160, 450, TAN, DARK_BROWN, thick=True)

        # Decorative corners
        corner_size = 20
        corners = [(90, 160), (self.width - 110, 160), (90, 580), (self.width - 110, 580)]
        for cx, cy in corners:
            pygame.draw.rect(self.screen, DARK_BROWN, (cx, cy, corner_size, corner_size))

        # Resolution text
        self.draw_text(
            resolution_text, self.body_font, DARK_BROWN, 120, 200, max_width=self.width - 240
        )

        # Continue prompt
        self.draw_panel(self.width // 2 - 250, 650, 500, 70, DARK_BLUE, BRIGHT_YELLOW, thick=True)
        self.draw_text(
            "[SPACE] Continue Journey",
            self.heading_font,
            OFF_WHITE,
            self.width // 2,
            685,
            center=True,
        )

    def render_game_over_screen(self, game_state: GameState):
        if game_state.victory:
            self.screen.fill(PLAINS_GREEN)
            title = "🎉 VICTORY! 🎉"
            message = f"You reached Oregon City after {game_state.day} days!"
            banner_color = DARK_BLUE
            border_color = GOLD
        else:
            self.screen.fill(DARK_GRAY)
            title = "💀 GAME OVER 💀"
            if game_state.food <= 0:
                message = "Your party starved on the trail..."
            else:
                message = "Your party did not survive the journey..."
            banner_color = BLACK
            border_color = BRIGHT_RED

        # Title banner
        self.draw_panel(
            self.width // 2 - 400, 100, 800, 120, banner_color, border_color, thick=True
        )
        self.draw_text(title, self.title_font, border_color, self.width // 2, 160, center=True)

        # Message
        self.draw_text(message, self.heading_font, OFF_WHITE, self.width // 2, 260, center=True)

        # Stats panel
        self.draw_panel(self.width // 2 - 350, 340, 700, 280, TAN, DARK_BROWN, thick=True)
        self.draw_text(
            "📊 JOURNEY STATISTICS",
            self.heading_font,
            DARK_BROWN,
            self.width // 2,
            365,
            center=True,
        )

        y_offset = 420
        self.draw_text(
            f"📅 Days Traveled: {game_state.day}",
            self.body_font,
            DARK_BROWN,
            self.width // 2 - 200,
            y_offset,
        )
        y_offset += 50
        self.draw_text(
            f"🗺️  Miles Covered: {game_state.miles_traveled}",
            self.body_font,
            DARK_BROWN,
            self.width // 2 - 200,
            y_offset,
        )
        y_offset += 50

        survivors = len([m for m in game_state.party if m.health > 0])
        survivor_color = GREEN if survivors > 2 else (ORANGE if survivors > 0 else RED)
        self.draw_text(
            f"👥 Survivors: {survivors} / {len(game_state.party)}",
            self.body_font,
            survivor_color,
            self.width // 2 - 200,
            y_offset,
        )

        # Controls
        self.draw_panel(self.width // 2 - 300, 660, 600, 80, BLACK, GOLD, thick=True)
        self.draw_text(
            "[R] Restart  •  [Q] Quit",
            self.heading_font,
            BRIGHT_YELLOW,
            self.width // 2,
            700,
            center=True,
        )

    def render_inventory_screen(self, game_state: GameState, item_catalog: ItemCatalog):
        # Inventory background
        self.screen.fill(DARK_BROWN)

        # Title
        self.draw_panel(self.width // 2 - 250, 20, 500, 80, TAN, GOLD, thick=True)
        self.draw_text(
            "🎒 INVENTORY 🎒", self.title_font, DARK_BROWN, self.width // 2, 60, center=True
        )

        # Resources panel
        self.draw_panel(40, 120, self.width - 80, 180, TAN, DARK_BROWN, thick=True)
        self.draw_text("Resources", self.heading_font, DARK_BROWN, 70, 140)

        y = 190
        self.draw_pixel_icon("food", 70, y, 32)
        self.draw_text(f"Food: {game_state.food} lbs", self.body_font, DARK_BROWN, 115, y + 5)

        self.draw_pixel_icon("water", 450, y, 32)
        self.draw_text(f"Water: {game_state.water} gal", self.body_font, DARK_BROWN, 495, y + 5)

        self.draw_pixel_icon("ammo", 830, y, 32)
        self.draw_text(f"Ammo: {game_state.ammo}", self.body_font, DARK_BROWN, 875, y + 5)

        y += 55
        self.draw_pixel_icon("wagon", 70, y, 32)
        self.draw_text(f"Wagon: {game_state.wagon_health}%", self.body_font, DARK_BROWN, 115, y + 5)

        self.draw_text(f"Money: ${game_state.money}", self.body_font, ORANGE, 450, y + 5)

        # Items panel
        self.draw_panel(40, 320, self.width - 80, 400, TAN, DARK_BROWN, thick=True)
        self.draw_text("Special Items", self.heading_font, DARK_BROWN, 70, 340)

        y_offset = 390
        if game_state.inventory:
            col = 0
            for item_id, quantity in sorted(game_state.inventory.items()):
                item_name = item_catalog.get_name(item_id)
                x = 70 + (col * 350)
                self.draw_text(
                    f"• {item_name} x{quantity}", self.body_font, DARK_BROWN, x, y_offset
                )

                col += 1
                if col >= 3:
                    col = 0
                    y_offset += 40
                    if y_offset > 680:
                        break
        else:
            self.draw_text("No special items", self.body_font, GRAY, 70, y_offset)

        # Return hint
        self.draw_text(
            "[ESC] Return to Trail", self.body_font, OFF_WHITE, self.width // 2, 750, center=True
        )

    def update(self):
        pygame.display.flip()
        self.clock.tick(60)

    def quit(self):
        pygame.quit()
