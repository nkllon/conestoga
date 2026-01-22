# Research Log — core-game

## Summary
- Applied light discovery (extension of existing Pygame/Gemini core) to align with current game loop and fallback patterns.
- Confirmed primary integration points: `ConestogaGame` state machine, `GeminiGateway` boundary, `EventDraft/EventResolution` schemas, `FallbackDeck`.
- No new external dependencies needed; continue using Gemini 3 via `google-genai` with fallback; Docker only for testing harness if used.

## Topics & Findings
- **Extension Points**: `src/conestoga/game/runner.py` orchestrates modes; `gemini_gateway.py` mediates all LLM calls; `events.py` owns schemas and fallback content; `state.py` enforces inventory/catalog invariants; `ui.py` logs and renders.
- **Dependencies**: `google-genai` (Gemini 3 models) with `.env`-backed key; `pygame-ce` for loop/UI. Retry count (2) and model default (`gemini-3-flash-preview`) already set; must preserve validation and fallback behavior.
- **Patterns to Preserve**: Prefetch-first event generation, on-demand resolutions, validation before mutation, fallback on failure/timeout/quota, UI log updates on state changes.
- **Risks**: LLM JSON drift; race conditions in prefetch thread; UI hangs if loading indicators not updated; resource exhaustion toggling.
- **Testing Focus**: Deterministic seeds; stub Gemini at boundary only; validate fallback paths; verify thread-safe prefetch and timeout handling; use Docker services only if integration surfaces expand (none required now).

## Decisions (for Design)
- Keep Gemini boundary in `GeminiGateway`; no direct model calls elsewhere.
- Maintain background prefetch thread and locking; expose clean cancellation/reset hooks.
- Enforce schema validation before applying effects; catalog check on items; log every fallback activation for observability.
- UI must reflect loading, selection state, and resource deltas before returning to TRAVEL mode.
