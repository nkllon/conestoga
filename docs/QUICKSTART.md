# Conestoga Game - Quick Start

## Overview

Conestoga is an Oregon Trail-inspired journey simulation powered by **Gemini 3 API** for dynamic event generation.

**Important:** This game requires Gemini 3 models. All AI-generated events use `gemini-3-flash-preview` or `gemini-3-pro-preview`.

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
- `SPACE` - Advance one day (triggers event prefetch)
- `I` - View inventory
- `Q` - Quit game

### Loading Screen (during event generation)
- `ESC` - Cancel and use fallback event
- Wait indicator shows elapsed time
- Auto-fallback after 5 seconds

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

## Gemini 3 Integration

The game uses **Gemini 3 API** (`gemini-3-flash-preview`) for dynamic event generation with **async prefetch** to minimize wait times.

### Performance Features (Requirement 10)

- **Async Prefetch**: Events are generated in background threads while you travel
- **Non-blocking UI**: Game remains responsive during API calls (maintains 60 FPS)
- **Loading Indicator**: Shows animated progress when waiting for events
- **Smart Timeout**: Automatically falls back to local events after 5 seconds
- **Cancellation**: Press ESC during loading to use fallback event immediately
- **Target Latency**: 80% of events complete within 2 seconds

### How It Works

1. **During Travel**: When an event is likely, the game prefetches it in the background
2. **Event Trigger**: If prefetch is ready, event appears instantly
3. **Loading State**: If not ready, shows animated loading screen
4. **Seamless Transition**: Event appears as soon as generation completes

### Setup Gemini API

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)
2. Set your API key:

```bash
export GEMINI_API_KEY='your-api-key-here'
```

Or create a `.env` file:
```bash
GEMINI_API_KEY='your-api-key-here'
```

**Note:** The game uses Gemini 3 models exclusively. Without an API key, it falls back to a curated set of 5 local events.

### Fallback Mode

If no API key is provided, the game runs in fallback mode with deterministic local events. This ensures the game is always playable for demo purposes.
export GEMINI_API_KEY="your-api-key"
conestoga
```

See [requirements.md](../requirements.md), [design.md](../design.md), and [research.md](../research.md) for full project documentation.
