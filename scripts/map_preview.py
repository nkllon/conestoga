#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import sys

import pygame


def parse_args():
    parser = argparse.ArgumentParser(
        description="Preview the Oregon Trail map asset (headless-friendly)."
    )
    parser.add_argument("--headless", action="store_true", help="Force dummy SDL video driver")
    parser.add_argument(
        "--seconds",
        type=float,
        default=3.0,
        help="How long to keep the preview window open (non-headless only).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Window width for scaling the map preview.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=600,
        help="Window height for scaling the map preview.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.display.init()
    pygame.init()

    size = (args.width, args.height)
    try:
        screen = pygame.display.set_mode(size)
    except pygame.error as exc:
        print(f"❌ Unable to initialize display: {exc}", file=sys.stderr)
        if args.headless:
            print("Try a real display or install a dummy SDL driver.", file=sys.stderr)
        return 1

    map_path = Path(__file__).resolve().parents[1] / "assets" / "oregon_trail_map.png"
    if not map_path.exists():
        print(f"❌ Map asset missing at {map_path}", file=sys.stderr)
        return 1

    map_img = pygame.image.load(map_path.as_posix())
    scaled = pygame.transform.scale(map_img, size)
    screen.blit(scaled, (0, 0))
    pygame.display.set_caption("Conestoga Map Preview")
    pygame.display.flip()

    print(f"✅ Map loaded and rendered at {size}")
    print(f"   Asset path: {map_path}")
    print(f"   Original size: {map_img.get_size()}")

    if args.headless:
        print("Headless mode: window not displayed.")
    else:
        print(f"Previewing for {args.seconds:.1f} seconds (Ctrl+C to exit sooner).")
        clock = pygame.time.Clock()
        remaining_ms = int(args.seconds * 1000)
        while remaining_ms > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    remaining_ms = 0
                    break
            clock.tick(30)
            remaining_ms -= clock.get_time()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
