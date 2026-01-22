# Conestoga Game - Quick Start

## Installation

1. Install dependencies using UV:
```bash
uv sync
```

Or with pip:
```bash
pip install -e .
```

## Running the Game

After installation, you can run the game using:

```bash
conestoga
```

Or directly:
```bash
uv run conestoga
```

Or with Python:
```bash
python -m conestoga.game.runner
```

## Controls

### Travel Screen
- `SPACE` - Advance one day
- `I` - View inventory
- `Q` - Quit game

### Event Screen
- `UP/DOWN` - Select choice
- `ENTER` or `1-5` - Confirm choice

### Resolution Screen
- `SPACE` - Continue

### Inventory Screen
- `ESC` - Return to travel

### Game Over Screen
- `R` - Restart
- `Q` - Quit

## Running Tests

```bash
uv run pytest
```

Or:
```bash
pytest
```

## Goal

Travel 2000 miles to Oregon while managing resources and making decisions during events.

### Win Condition
- Reach 2000 miles

### Lose Conditions
- Food reaches 0 (party starves)
- All party members die

## Gemini Integration

The game is designed to use Gemini API for dynamic event generation. Currently runs in fallback mode with curated events.

To enable Gemini API:
```bash
export GEMINI_API_KEY="your-api-key"
conestoga
```

See [requirements.md](../requirements.md), [design.md](../design.md), and [research.md](../research.md) for full project documentation.
