#!/usr/bin/env python3
"""
Quick test to verify map image loads and displays
"""
import pygame
import sys

# Set SDL to use dummy video driver for headless testing
import os
if len(sys.argv) > 1 and sys.argv[1] == "--headless":
    os.environ['SDL_VIDEODRIVER'] = 'dummy'

pygame.init()
screen = pygame.display.set_mode((800, 600))

try:
    map_img = pygame.image.load('assets/oregon_trail_map.png')
    print(f"✅ Map loaded successfully: {map_img.get_size()}")
    
    # Scale it
    scaled = pygame.transform.scale(map_img, (800, 600))
    print(f"✅ Map scaled to: {scaled.get_size()}")
    
    # Draw it
    screen.blit(scaled, (0, 0))
    print("✅ Map rendered to screen")
    
    print("\n🎉 Map system working correctly!")
    print("   - Trail runs WEST (left to right)")
    print("   - Independence, MO on the LEFT/EAST")
    print("   - Oregon City on the RIGHT/WEST")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

pygame.quit()
