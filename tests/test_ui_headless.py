import pygame


def test_gameui_loading_and_event_render_headless(monkeypatch):
    # Run Pygame headless (default for tests)
    monkeypatch.setenv("UI_HEADLESS", "1")

    from conestoga.game.events import Choice, EventDraft
    from conestoga.game.state import GameState
    from conestoga.game.ui import GameUI  # imported after env vars set

    ui = GameUI(width=800, height=600)
    state = GameState()
    # Loading screen should not crash
    ui.render_loading_screen(1.2)

    event = EventDraft(
        event_id="evt",
        title="Test Event",
        narrative="A simple headless render",
        choices=[Choice(id="c1", text="Go left"), Choice(id="c2", text="Go right")],
    )
    ui.render_event_screen(event, state, selected_choice=1)
    ui.quit()
    pygame.quit()
