# Tech
- **Languages & Runtime**: Python 3.12; packaging via `uv`; console entry `conestoga` (uv script) or `uv run python -m conestoga.main`.
- **UI & Loop**: Pygame CE drives the main loop and rendering (`GameUI`); game flow orchestrated in `ConestogaGame` with a simple state machine (`TRAVEL/LOADING/EVENT/RESOLUTION/INVENTORY/GAME_OVER`).
- **LLM Integration**: `GeminiGateway` isolates Gemini 3 API (gemini-3-flash-preview by default), validates JSON responses, retries up to 2x, and falls back to `FallbackDeck` on errors/quotas/missing keys. `.env` via `python-dotenv`; `GEMINI_API_KEY` optional for offline fallback.
- **Data & Validation**: `EventDraft`/`EventResolution` schemas enforce allowed effect types; `ItemCatalog` guards inventory consistency; background prefetch thread hydrates the next event while UI runs.
- **Tooling**: Ruff (line length 100, import order, pyupgrade, bugbear), pytest (`tests/`), Make targets (`install-dev`, `run`, `lint`, `format`, `test`), npm used only for `cc-sdd` scaffolding.
- **Resilience**: Graceful degradation to deterministic fallback content when Gemini is unavailable; resource exhaustion flag prevents repeated failing calls.

