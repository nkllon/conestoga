# UI Design Guide

## Aesthetic Philosophy

The Conestoga UI features a **retro pixel art** aesthetic inspired by classic Oregon Trail games, with:

- 🎨 **Vibrant color palette** - Rich earth tones, bright accents
- 🖼️ **Chunky borders** - Thick pixel-perfect frames (4-6px)
- 🎯 **3D depth effects** - Inner highlights for dimensionality  
- 🎮 **Icon system** - Hand-drawn pixel art sprites
- 📜 **Visual hierarchy** - Clear separation of UI zones
- ⚡ **High contrast** - Easy readability

## Color Palette

### Terrain Colors
- **Ocean Blue** `#2980B9` - Water, sky
- **Plains Green** `#76D760` - Grasslands
- **Forest Green** `#229954` - Dense vegetation
- **Desert Tan** `#E6B058` - Arid regions
- **Mountain Gray** `#95A5A6` - Rocky peaks
- **River Blue** `#3498DB` - Waterways

### UI Colors
- **Gold** `#FFD700` - Titles, highlights
- **Bright Yellow** `#F1C40F` - Attention, borders
- **Orange** `#E67E22` - Selection, warnings
- **Red** `#E74C3C` - Danger, critical
- **Bright Red** `#C0392B` - Game over, locks
- **Green** `#27AE60` - Health, success
- **Dark Brown** `#5C4033` - Panels, frames
- **Tan** `#D2B48C` - Parchment, backgrounds
- **Off White** `#F0EAD6` - Text, readability

## Screen Layouts

### Travel Screen (Main Hub)
```
┌─────────────────────────────────────────────────┐
│         🚌 CONESTOGA (Title Banner)            │
├─────────────────────────────────────────────────┤
│  Day 5 | Miles 250/2000 [███████░░░░] 12%     │
├──────────────────┬──────────────────────────────┤
│   RESOURCES      │     PARTY STATUS             │
│   🍞 Food: 200   │  ❤️ John: 85% [████████░░]  │
│   💧 Water: 50   │  ❤️ Mary: 92% [█████████░]  │
│   🔫 Ammo: 40    │  ❤️ Sam: 78%  [███████░░░]  │
│   🚌 Wagon: 75%  │  ❤️ Beth: 88% [████████░░]  │
├──────────────────┴──────────────────────────────┤
│  🌾 Plains | ☀️ Clear Weather                  │
├─────────────────────────────────────────────────┤
│         ⌨️ CONTROLS                             │
│   [SPACE] Travel • [I] Inventory • [Q] Quit    │
└─────────────────────────────────────────────────┘
```

### Event Screen (Crisis)
```
┌─────────────────────────────────────────────────┐
│         ⚠️  EVENT  ⚠️                           │
│         River Crossing Ahead                    │
├─────────────────────────────────────────────────┤
│  The river is swollen from recent rains...     │
│  Your wagon will need to cross carefully.      │
├─────────────────────────────────────────────────┤
│         ⚔️ Choose Your Action:                  │
├─────────────────────────────────────────────────┤
│  ① Ford the river carefully                    │ ← Selected
├─────────────────────────────────────────────────┤
│  ② Wait for the water to recede                │
├─────────────────────────────────────────────────┤
│  ③ Build a raft ($20)                          │
│     🔒 Not enough money                         │
└─────────────────────────────────────────────────┘
```

### Loading Screen (Async Generation)
```
┌─────────────────────────────────────────────────┐
│                                                 │
│         🎲 Generating Event...                  │
│         Gemini 3 AI at work...                  │
│                                                 │
│              🚌 → → →                           │
│                                                 │
│              ⏱️ 2.3s                            │
│                                                 │
│              [Spinning Wheel]                   │
│                                                 │
│         [ESC] Use Fallback Event                │
└─────────────────────────────────────────────────┘
```

## Pixel Art Icons

The UI includes hand-drawn pixel art icons (24-48px):

- **🚌 Wagon** - Covered wagon with wheels
- **🍞 Food** - Bread loaf
- **💧 Water** - Water droplet
- **🔫 Ammo** - Bullet
- **❤️ Heart** - Health indicator
- **⛰️ Mountain** - Mountain peak with snow
- **🏰 Fort** - Fort building

## Visual Effects

### Panel Borders
- **Thick borders** (4-6px) for retro chunky look
- **Inner highlights** for 3D depth effect
- **Double borders** for important panels

### Text Styling
- **Large pixel fonts** (24-64px) for readability
- **High contrast** text on backgrounds
- **Color coding**:
  - Gold/Yellow: Titles, important info
  - Off-White: Body text
  - Red: Warnings, danger
  - Green: Positive stats
  - Gray: Disabled/hints

### Animations
- **Spinning wagon wheels** - Loading indicator
- **Moving wagon train** - Progress visualization
- **Animated dots** - Text loading states
- **Progress bars** - Health, journey completion

## Responsive Elements

### Choice Buttons
- **Orange background** when selected
- **Gold border** for active choice
- **Gray** for unavailable choices
- **Numbered badges** with circular design

### Health Bars
- **Green** (>50% health)
- **Orange** (20-50% health)
- **Red** (<20% health)
- **Animated fill** based on current value

### Status Indicators
- Icons before text (wagon, food, water, etc.)
- Color-coded values
- Real-time updates

## Design Principles

1. **Clarity First** - Information hierarchy is clear
2. **Retro Charm** - Pixel art aesthetic throughout
3. **Functional Beauty** - Every element serves a purpose
4. **Consistent Spacing** - Generous padding and margins
5. **Color Psychology** - Appropriate colors for context
6. **Visual Feedback** - Clear selected/hover states
7. **Accessibility** - High contrast, readable fonts

## Resolution & Scaling

- **Base Resolution**: 1200x800 (4:3 aspect ratio)
- **Font Scaling**: Pixel-perfect sizing (24, 32, 40, 64)
- **Icon Sizes**: 24px (small), 32px (medium), 48px (large)
- **Panel Padding**: 20px minimum

## Future Enhancements

Potential additions to enhance the pixel art aesthetic:

- [ ] Animated weather effects (rain drops, snow)
- [ ] Parallax scrolling backgrounds
- [ ] Particle effects (dust, campfire)
- [ ] Day/night cycle color shifts
- [ ] Sound effects and retro music
- [ ] Portrait sprites for party members
- [ ] Mini-map visualization
- [ ] Achievement badges/ribbons
- [ ] Terrain transition animations
