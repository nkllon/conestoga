from pathlib import Path

import pygame
import pytest


def test_map_image_loads_and_renders_headless(monkeypatch):
    """Ensure the map asset loads, scales, and blits without opening a real window."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.init()

    try:
        try:
            screen = pygame.display.set_mode((800, 600))
        except pygame.error as exc:
            pytest.skip(f"dummy video driver unavailable: {exc}")

        map_path = Path(__file__).resolve().parents[1] / "assets" / "oregon_trail_map.png"
        assert map_path.exists(), "Map asset missing"

        map_img = pygame.image.load(map_path.as_posix())
        assert map_img.get_width() > 0 and map_img.get_height() > 0

        scaled = pygame.transform.scale(map_img, (800, 600))
        assert scaled.get_size() == (800, 600)

        screen.blit(scaled, (0, 0))
        pygame.display.flip()
    finally:
        pygame.display.quit()
        pygame.quit()
