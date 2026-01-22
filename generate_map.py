#!/usr/bin/env python3
"""
Generate Oregon Trail map image
"""

from PIL import Image, ImageDraw, ImageFont

# Create image
width, height = 1200, 600
img = Image.new("RGB", (width, height), color="#2980b9")  # Ocean blue
draw = ImageDraw.Draw(img)

# US landmass (simplified)
landmass = [
    (100, 150),
    (200, 120),
    (400, 100),
    (600, 110),
    (800, 130),
    (1000, 140),
    (1150, 165),  # North
    (1150, 450),
    (1050, 520),
    (800, 540),
    (500, 530),
    (250, 510),
    (150, 450),
    (100, 150),  # South loop
]
draw.polygon(landmass, fill="#76d35c", outline="#5a8a47")  # Plains green

# Terrain regions
# Desert (southwest)
desert = [(250, 450), (500, 470), (550, 530), (300, 520)]
draw.polygon(desert, fill="#e6b058")  # Desert tan

# Mountains (Rockies - center-west)
for i in range(10):
    mx = 550 + i * 45
    my = 200 + (i % 3) * 30
    mw = 40
    mh = 120
    mountain = [(mx, my + mh), (mx + mw // 2, my), (mx + mw, my + mh)]
    draw.polygon(mountain, fill="#95a5a6", outline="#7f8c8d")
    # Snow cap
    snow = [(mx + mw // 2, my), (mx + mw * 0.35, my + mh * 0.4), (mx + mw * 0.65, my + mh * 0.4)]
    draw.polygon(snow, fill="#ecf0f1")

# Forests (Pacific Northwest)
for i in range(8):
    fx = 900 + (i % 4) * 50
    fy = 150 + (i // 4) * 80
    draw.rectangle([fx, fy, fx + 45, fy + 70], fill="#229954", outline="#1e7e4a")

# Rivers
# Missouri River
missouri = [(350, 250), (420, 270), (480, 290), (530, 310)]
draw.line(missouri, fill="#3498db", width=8)

# Platte River
platte = [(530, 310), (600, 320), (680, 325), (750, 330)]
draw.line(platte, fill="#3498db", width=8)

# Snake/Columbia River
snake = [(750, 330), (820, 310), (900, 280), (980, 250), (1050, 220)]
draw.line(snake, fill="#3498db", width=8)

# The Oregon Trail (brown path from Independence, MO to Oregon City)
# WESTWARD TRAVEL = RIGHT TO LEFT on map
trail_points = [
    (1050, 280),  # Independence, MO (EAST - right side)
    (990, 290),  # Kansas
    (930, 305),  # Nebraska
    (870, 315),  # Fort Kearny
    (810, 325),  # Platte River
    (750, 330),  # Chimney Rock
    (690, 335),  # Fort Laramie
    (630, 325),  # South Pass
    (570, 310),  # Fort Bridger
    (510, 285),  # Fort Hall
    (450, 260),  # Snake River
    (390, 230),  # Fort Boise
    (330, 200),  # The Dalles
    (280, 180),  # Oregon City (WEST - left side)
]

# Draw trail as thick brown line
draw.line(trail_points, fill="#8b4513", width=12)
# Add edge highlight
draw.line(trail_points, fill="#d2b48c", width=6)

# Add landmarks with circles
landmarks = [
    (1050, 280, "Independence"),
    (870, 315, "Ft Kearny"),
    (690, 335, "Ft Laramie"),
    (630, 325, "S Pass"),
    (510, 285, "Ft Hall"),
    (280, 180, "Oregon City"),
]

try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
except Exception:
    font = ImageFont.load_default()
    small_font = ImageFont.load_default()

for x, y, name in landmarks:
    # Fort marker
    draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill="#c0392b", outline="#000000")
    # Label
    bbox = draw.textbbox((0, 0), name, font=small_font)
    text_width = bbox[2] - bbox[0]
    draw.text((x - text_width // 2, y + 12), name, fill="#000000", font=small_font)

# Add compass rose (top right)
compass_x, compass_y = width - 80, 40
draw.text((compass_x - 10, compass_y), "N", fill="#000000", font=font)
draw.text((compass_x - 10, compass_y + 60), "S", fill="#000000", font=font)
draw.text((compass_x - 40, compass_y + 30), "W", fill="#000000", font=font)
draw.text((compass_x + 20, compass_y + 30), "E", fill="#000000", font=font)
draw.line([(compass_x, compass_y + 15), (compass_x, compass_y + 55)], fill="#000000", width=2)
draw.line(
    [(compass_x - 30, compass_y + 35), (compass_x + 30, compass_y + 35)], fill="#000000", width=2
)

# Save
img.save("assets/oregon_trail_map.png")
print("✅ Map saved to assets/oregon_trail_map.png")
print(f"   Size: {width}x{height}")
print("   Trail runs WEST (right to left): Independence, MO → Oregon City")
