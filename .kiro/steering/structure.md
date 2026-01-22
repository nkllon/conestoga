# Structure
- **Game Package**: `src/conestoga/game/` holds domain logic—`runner.py` orchestrates the loop and modes; `events.py` defines event/resolution schemas and fallback content; `gemini_gateway.py` is the only boundary to Gemini; `state.py` manages inventory, party, and invariants; `ui.py` renders/logs via Pygame.
- **Entry Points**: CLI script `conestoga` and module entry `python -m conestoga.main` both construct `ConestogaGame`; keep side effects within these entrypoints to avoid import-time IO.
- **Patterns**: Event flow is prefetch-first (background thread populates the next `EventDraft`, resolutions on-demand). Validation happens before state mutation; fallback deck is the default when validation fails or API is offline.
- **Testing Layout**: Pytest specs live in `tests/` (e.g., `test_game.py`); prefer deterministic tests by seeding randomness and stubbing Gemini calls.
- **Assets & Docs**: Visual/audio assets under `assets/`; design and research notes in `design.md`, `UI_DESIGN.md`, `research.md`; generated scaffolding from `cc-sdd` lives outside gameplay code and should not alter runtime behavior.

