"""
Conestoga - Main Game Runner
Entry point for the Conestoga game
Implements Requirement 10: Async prefetch and non-blocking UI
"""

import random
import threading
import time
from enum import Enum

import pygame

from .events import EventDraft, EventResolution, FallbackDeck
from .fallback_monitor import FallbackMonitor
from .gemini_gateway import GeminiGateway
from .state import GameState, ItemCatalog
from .ui import GameUI


class GameMode(Enum):
    """Game state machine modes"""

    TRAVEL = "travel"
    LOADING = "loading"  # Req 10.2: Loading state during async fetch
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
        self.fallback_monitor = FallbackMonitor()

        self.mode = GameMode.TRAVEL
        self.current_event: EventDraft | None = None
        self.current_resolution: str | None = None
        self.current_resolutions: dict[
            str, EventResolution
        ] = {}  # Cached resolutions for current event
        self.selected_choice_index = 0

        self.days_since_event = 0
        self.event_frequency = 3

        # Req 10.1: Async prefetch support
        self.prefetch_thread: threading.Thread | None = None
        self.prefetch_event: EventDraft | None = None
        self.prefetch_lock = threading.Lock()
        self.prefetch_cancelled = False
        self.loading_start_time: float | None = None
        self.loading_timeout = 5.0  # Req 10.6: Fallback after timeout

        print("=" * 60)
        print("CONESTOGA - Oregon Trail Journey Simulation")
        print("=" * 60)
        # Refresh Gemini API status on each game load
        gemini_status = self.gemini.is_online()
        self.ui.gemini_online = gemini_status
        print(f"Gemini API: {'ONLINE' if gemini_status else 'OFFLINE (Fallback Mode)'}")
        if self.gemini.resource_exhausted:
            print("(API quota exhausted - using fallback deck)")
        print(f"Starting journey to Oregon - {self.game_state.target_miles} miles ahead!")
        print("=" * 60)
        self._sync_gemini_status()

        # Start initial prefetch during game load
        print("[Init] Prefetching first event...")
        self.start_prefetch()

        # Add welcome to event log
        self.ui.add_to_log(
            "The wagons are packed. Your family stands at the edge of Independence, "
            "Missouri, gazing westward.",
            "success",
        )
        self.ui.add_to_log(
            f"{len(self.game_state.party)} souls brave enough to chase the promise of "
            f"Oregon. The trail awaits.",
            "info",
        )
        self.ui.add_to_log(
            "'It's 2,000 miles to Oregon City,' the guide warns. 'May fortune favor you.'", "info"
        )

    def should_trigger_event(self) -> bool:
        self.days_since_event += 1
        chance = min(0.8, self.days_since_event / self.event_frequency)
        return random.random() < chance

    def _sync_gemini_status(self):
        """Update UI Gemini status and log offline transition once."""
        self.ui.gemini_online = self.gemini.is_online()
        if not self.ui.gemini_online and self.fallback_monitor.should_notify_offline():
            self.ui.add_to_log("Gemini offline or quota exhausted. Using fallback deck.", "warning")
            self.fallback_monitor.mark_offline_notified()

    def _log_fallback(self, kind: str, reason: str | None = None):
        """Surface fallback usage to the player log."""
        msg = f"Fallback {kind} used"
        if reason:
            msg += f" ({reason})"
        self.ui.add_to_log(msg, "warning")

    def _prefetch_worker(self):
        """Req 10.1: Background thread for async event + resolutions generation"""
        try:
            if self.prefetch_cancelled:
                return

            print("[Prefetch] Generating event...")
            event = self.gemini.generate_event_draft(
                self.game_state, self.item_catalog, tier="minor"
            )

            if self.prefetch_cancelled:
                return

            errors = event.validate(self.item_catalog)
            if errors:
                print(f"[Warning] Event validation errors: {errors}")
                fallback = FallbackDeck()
                event = fallback.get_random_event(self.game_state)
                self.gemini.last_event_source = "fallback"
                self.gemini.last_failure_reason = "; ".join(errors)

            # Event prefetch complete - resolutions generated on-demand
            # This provides fast initial load (~5-15s vs ~60s for all resolutions)
            with self.prefetch_lock:
                if not self.prefetch_cancelled:
                    self.prefetch_event = event
                    print(f"[Prefetch] Complete: {event.title}")
                    if self.gemini.last_event_source == "fallback":
                        self.fallback_monitor.record_event(
                            "fallback", self.gemini.last_failure_reason
                        )
        except Exception as e:
            print(f"[Prefetch] Error: {e}")
            with self.prefetch_lock:
                if not self.prefetch_cancelled:
                    fallback = FallbackDeck()
                    self.prefetch_event = fallback.get_random_event(self.game_state)
                    self.gemini.last_event_source = "fallback"
                    self.gemini.last_failure_reason = str(e)
                    self.fallback_monitor.record_event("fallback", str(e))

    def start_prefetch(self):
        """Req 10.1: Start async event prefetch"""
        if self.prefetch_thread and self.prefetch_thread.is_alive():
            return  # Already fetching

        self.prefetch_cancelled = False
        self.prefetch_event = None
        self.prefetch_resolutions = {}
        self.prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
        self.prefetch_thread.start()
        print("[Prefetch] Started background event generation")

    def trigger_event(self):
        """Req 10.2-10.3: Use prefetched event or show loading state"""
        print(f"\n[Day {self.game_state.day}] Event triggered!")

        # Dramatic event introduction
        intros = [
            "The trail ahead is blocked...",
            "Something's wrong. The wagon master calls a halt.",
            "A commotion up ahead. Everyone stops.",
            "The oxen bellow and refuse to move. What now?",
            "Trouble on the horizon.",
        ]
        self.ui.add_to_log(random.choice(intros), "warning")
        self.ui.add_to_log("The trail master signals everyone to gather round...", "info")

        with self.prefetch_lock:
            if self.prefetch_event:
                # Req 10.3: Use prefetched event immediately
                self.current_event = self.prefetch_event
                self.current_resolutions = {}  # Resolutions generated on-demand
                self.prefetch_event = None
                self.selected_choice_index = 0
                self.mode = GameMode.EVENT
                self.days_since_event = 0
                print(f"[Event] Using prefetched: {self.current_event.title}")
                if self.gemini.last_event_source == "fallback":
                    self.fallback_monitor.record_event("fallback", self.gemini.last_failure_reason)
                    self._log_fallback("event", self.gemini.last_failure_reason)
                self._sync_gemini_status()
                # Start prefetching next event
                self.start_prefetch()
                return

        # Req 10.2: Show loading state if event not ready
        self.mode = GameMode.LOADING
        self.loading_start_time = time.time()
        print("[Loading] Waiting for event generation...")

        # Start generation if not already running
        if not self.prefetch_thread or not self.prefetch_thread.is_alive():
            self.start_prefetch()

    def resolve_choice(self, choice_index: int):
        if not self.current_event:
            return

        choice = self.current_event.choices[choice_index]

        if not choice.is_available(self.game_state):
            print(f"[Warning] Choice not available: {choice.get_lock_reason(self.game_state)}")
            return

        print(f"[Choice] Selected: {choice.text}")

        # Add player choice to narrative log
        self.ui.add_to_log(f"You decide: {choice.text}", "info")

        # Check if we already generated this resolution
        if choice.id in self.current_resolutions:
            resolution = self.current_resolutions[choice.id]
            print("[Resolution] Using cached resolution")
        else:
            # Generate resolution on-demand (with loading screen)
            print(f"[Resolution] Generating for choice: {choice.id}")
            resolution = self.gemini.generate_event_resolution(
                self.current_event, choice.id, self.game_state, self.item_catalog
            )
            # Cache it for potential retry
            if resolution:
                self.current_resolutions[choice.id] = resolution

        if not resolution:
            self.current_resolution = "You make your choice and move on."
        else:
            self.current_resolution = resolution.apply(self.game_state)
            print(f"[Resolution] {self.current_resolution}")
            # Add outcome to event log
            if self.current_resolution:
                outcome_preview = (
                    self.current_resolution.split(".")[0]
                    if "." in self.current_resolution
                    else self.current_resolution[:60]
                )
                self.ui.add_to_log(f"{outcome_preview}...", "info")
            if self.gemini.last_resolution_source == "fallback":
                self.fallback_monitor.record_resolution(
                    "fallback", self.gemini.last_failure_reason
                )
                self._log_fallback("resolution", self.gemini.last_failure_reason)

        self._sync_gemini_status()

        self.mode = GameMode.RESOLUTION

    def advance_travel(self):
        print(f"\n--- Day {self.game_state.day + 1} ---")

        miles_today = random.randint(12, 18)
        self.game_state.advance_day(miles_today)

        print(
            f"Traveled {miles_today} miles. Total: "
            f"{self.game_state.miles_traveled}/{self.game_state.target_miles}"
        )
        print(f"Food: {self.game_state.food}, Water: {self.game_state.water}")

        # Add narrative daily progress
        terrain_stories = {
            "plains": [
                f"The wagon wheels creak through another {miles_today} miles of endless grassland.",
                f"Day {self.game_state.day}: The prairie wind whispers across {miles_today} "
                f"miles of rolling hills.",
                f"Oxen plod steadily westward, covering {miles_today} miles. The horizon never "
                f"seems to change.",
            ],
            "forest": [
                f"Dense timber slows progress. Only {miles_today} miles gained through the "
                f"shadowy woods.",
                f"Day {self.game_state.day}: The forest trail winds {miles_today} miles deeper "
                f"into darkness.",
                f"Branches scrape the canvas as you push {miles_today} miles through the "
                f"wilderness.",
            ],
            "desert": [
                f"The merciless sun bears down. {miles_today} grueling miles across burning sand.",
                f"Day {self.game_state.day}: Heat shimmers on the horizon. {miles_today} miles "
                f"of thirst and dust.",
                f"Every mile is agony in this wasteland. Somehow, {miles_today} more behind you.",
            ],
            "mountains": [
                f"Steep grades and thin air. {miles_today} exhausting miles into the high country.",
                f"Day {self.game_state.day}: The peaks loom closer. {miles_today} miles of "
                f"treacherous climbing.",
                f"Ice cracks beneath the wheels. {miles_today} dangerous miles at altitude.",
            ],
            "river": [
                f"Following the river's course for {miles_today} miles. Water close, but "
                f"crossing still ahead.",
                f"Day {self.game_state.day}: The current roars nearby. {miles_today} miles "
                f"along the banks.",
            ],
        }

        terrain = self.game_state.biome.value
        if terrain in terrain_stories:
            self.ui.add_to_log(random.choice(terrain_stories[terrain]), "info")
        else:
            self.ui.add_to_log(
                f"Day {self.game_state.day}: Another {miles_today} miles closer to Oregon.", "info"
            )

        # Narrative resource warnings
        if self.game_state.food < 50:
            if self.game_state.food < 20:
                self.ui.add_to_log(
                    "The food barrel scrapes near empty. Hunger gnaws at everyone's belly.",
                    "danger",
                )
            else:
                self.ui.add_to_log(
                    f"Food stores dwindling ({self.game_state.food} lbs left). Should consider "
                    f"hunting soon.",
                    "warning",
                )

        if self.game_state.water < 20:
            if self.game_state.water < 10:
                self.ui.add_to_log(
                    "Canteens nearly dry. Lips crack. Eyes desperately scan for water.", "danger"
                )
            else:
                self.ui.add_to_log(
                    f"Water running low ({self.game_state.water} gallons). Must find a creek.",
                    "warning",
                )

        # Check party health
        sick_count = sum(1 for m in self.game_state.party if m.health < 50)
        if sick_count > 0:
            if sick_count == 1:
                sick_member = next(m for m in self.game_state.party if m.health < 50)
                self.ui.add_to_log(
                    f"{sick_member.name} looks pale and weak. Health declining.", "warning"
                )
            else:
                self.ui.add_to_log(
                    f"{sick_count} family members are ailing. Morale is low.", "warning"
                )

        if self.game_state.is_game_over:
            self.mode = GameMode.GAME_OVER
            if self.game_state.victory:
                print("\n*** VICTORY! You reached Oregon! ***")
                self.ui.add_to_log(
                    "The Willamette Valley spreads before you—green, fertile, endless!", "success"
                )
                self.ui.add_to_log(
                    f"Oregon City at last! After {self.game_state.day} days and "
                    f"{self.game_state.miles_traveled} miles, your family is safe.",
                    "success",
                )
                self.ui.add_to_log(
                    "The dream of a new life in Oregon is real. You survived the trail.", "success"
                )
            else:
                print("\n*** GAME OVER ***")
                if self.game_state.food <= 0:
                    self.ui.add_to_log(
                        "The last crumbs are gone. Starvation claims your family, one by one.",
                        "danger",
                    )
                    self.ui.add_to_log(
                        "Your bones will rest unmarked on the prairie, another tragedy of "
                        "the trail.",
                        "danger",
                    )
                elif all(m.health <= 0 for m in self.game_state.party):
                    self.ui.add_to_log(
                        "The final member of your party breathes their last.", "danger"
                    )
                    self.ui.add_to_log(
                        "The Oregon Trail has claimed another family. Only the wagon remains.",
                        "danger",
                    )
            return

        # Req 10.1: Prefetch event in background during travel
        if self.days_since_event >= self.event_frequency - 1:
            # Likely to trigger event soon, start prefetch
            if not self.prefetch_thread or not self.prefetch_thread.is_alive():
                self.start_prefetch()

        if self.should_trigger_event():
            self.trigger_event()

    def handle_travel_input(self, key: int):
        if key == pygame.K_SPACE:
            self.advance_travel()
        elif key == pygame.K_i:
            self.mode = GameMode.INVENTORY
        elif key == pygame.K_q:
            self.ui.running = False
        elif key == pygame.K_UP:
            # Scroll log up (show older messages)
            self.ui.log_scroll_offset += 1
        elif key == pygame.K_DOWN:
            # Scroll log down (show newer messages)
            self.ui.log_scroll_offset -= 1

    def handle_event_input(self, key: int):
        if not self.current_event:
            return

        if key == pygame.K_UP:
            self.selected_choice_index = (self.selected_choice_index - 1) % len(
                self.current_event.choices
            )
        elif key == pygame.K_DOWN:
            self.selected_choice_index = (self.selected_choice_index + 1) % len(
                self.current_event.choices
            )
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

    def handle_loading_input(self, key: int):
        """Req 10.5: Allow cancellation during loading"""
        if key == pygame.K_ESCAPE:
            print("[Loading] Cancelled by user, using fallback")
            self.prefetch_cancelled = True
            fallback = FallbackDeck()
            self.current_event = fallback.get_random_event(self.game_state)
            self.selected_choice_index = 0
            self.mode = GameMode.EVENT
            self.days_since_event = 0

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
        """Main game loop - Req 10.4: Maintain responsiveness at target FPS"""
        while self.ui.running:
            key = self.ui.handle_events()

            # Req 10.3: Check if prefetched event is ready during loading
            if self.mode == GameMode.LOADING:
                with self.prefetch_lock:
                    if self.prefetch_event:
                        self.current_event = self.prefetch_event
                        self.current_resolutions = self.prefetch_resolutions.copy()
                        self.prefetch_event = None
                        self.prefetch_resolutions = {}
                        self.selected_choice_index = 0
                        self.mode = GameMode.EVENT
                        self.days_since_event = 0
                        print(
                            f"[Loading] Event ready: {self.current_event.title} "
                            f"({len(self.current_resolutions)} resolutions)"
                        )
                        # Start prefetching next event
                        self.start_prefetch()
                    elif (
                        self.loading_start_time
                        and (time.time() - self.loading_start_time) > self.loading_timeout
                    ):
                        # Req 10.6: Timeout and fallback
                        print("[Loading] Timeout, using fallback event")
                        self.prefetch_cancelled = True
                        fallback = FallbackDeck()
                        self.current_event = fallback.get_random_event(self.game_state)
                        self.selected_choice_index = 0
                        self.mode = GameMode.EVENT
                        self.days_since_event = 0
                        self.gemini.last_event_source = "fallback"
                        self.gemini.last_failure_reason = "timeout"
                        self.fallback_monitor.record_event("fallback", "timeout")
                        self._log_fallback("event", "timeout")
                        self._sync_gemini_status()

            if key:
                if self.mode == GameMode.TRAVEL:
                    self.handle_travel_input(key)
                elif self.mode == GameMode.LOADING:
                    self.handle_loading_input(key)
                elif self.mode == GameMode.EVENT:
                    self.handle_event_input(key)
                elif self.mode == GameMode.RESOLUTION:
                    self.handle_resolution_input(key)
                elif self.mode == GameMode.INVENTORY:
                    self.handle_inventory_input(key)
                elif self.mode == GameMode.GAME_OVER:
                    self.handle_gameover_input(key)

            # Req 10.4: Render at consistent FPS regardless of background tasks
            if self.mode == GameMode.TRAVEL:
                self.ui.render_travel_screen(self.game_state)
            elif self.mode == GameMode.LOADING:
                elapsed = time.time() - self.loading_start_time if self.loading_start_time else 0
                self.ui.render_loading_screen(elapsed)
            elif self.mode == GameMode.EVENT:
                if self.current_event:
                    self.ui.render_event_screen(
                        self.current_event, self.game_state, self.selected_choice_index
                    )
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
