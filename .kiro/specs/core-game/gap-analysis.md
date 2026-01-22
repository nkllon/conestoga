# Gap Analysis — core-game

## Current State
- **Architecture/Patterns**: `ConestogaGame` drives Pygame loop and mode transitions; `GeminiGateway` isolates LLM calls with retries and fallback deck; `EventDraft/EventResolution/Choice` models with basic validation; `GameState/ItemCatalog` own resources/inventory; `GameUI` renders travel, events, loading, and logs.
- **Conventions**: Prefetch-first event generation; resolutions on-demand; validation invoked only on event drafts; console logging for failures; UI logs for travel and outcomes; threading for prefetch with a simple lock.
- **Integration surfaces**: Gemini 3 via `google-genai`; fallback deck in `events.py`; Pygame rendering; no persistence or external services besides Gemini.

## Requirement-to-Asset Map (with gaps)
- **1.1–1.4 Travel loop & logging**: `runner.advance_travel()` updates state and UI log; `GameUI.render_travel_screen` shows miles/day/party. **Gap**: Event/log updates not guaranteed “after each tick or event” (depends on log writes, not enforced).
- **2.1–2.4 Event generation & resilience**: `GeminiGateway.generate_event_draft` + fallback deck; timeout fallback in `run()`; `resource_exhausted` flag set but not acted on. **Gaps**: No enforcement of 2–3 choices for Gemini events; quota flag doesn’t prevent future calls or notify UI.
- **3.1–3.4 Choice resolution & effects**: Availability check in `resolve_choice`; resolutions applied via `EventResolution.apply`; catalog validation only during event draft prereqs. **Gaps**: Effects don’t validate item_ids/targets against `ItemCatalog`; `modify_resource` accepts arbitrary attribute names; no schema check on effect count/types per requirement.
- **4.1–4.4 UI feedback**: Loading screen, choice highlighting, resource panel present. **Gaps**: Timeout/fallback not surfaced in UI log; loading indicator only during LOADING mode (prefetched path skips visible cue).
- **5.1–5.3 Observability/Recovery**: Console prints for errors; no structured logging of fallback usage or quota-triggered offline mode to UI or state. **Gap**: No persistent flag/telemetry for fallback source (prefetch vs deck) or repeated failures → offline mode.

## Options
- **Option A: Extend existing components**  
  - Enforce choice count and effect validation inside `GeminiGateway`/`EventDraft.validate`; use catalog when parsing resolutions; guard `modify_resource` to known fields.  
  - Apply `resource_exhausted` to short-circuit future calls and set `ui.gemini_online=False` with UI log; log fallback source in runner/UI.  
  - **Trade-offs**: Minimal files; adds complexity to gateway and runner; threading remains shared.
- **Option B: New helper components**  
  - Add `ValidationEngine`/`Telemetry` modules for choice/effect checks, fallback/quota tracking, and UI/console logging; have runner/gateway delegate.  
  - **Trade-offs**: Cleaner separation and reuse; extra files; more wiring for UI updates.
- **Option C: Hybrid**  
  - Keep gateway parsing but add a small `LLMPolicy`/`Validator` helper plus `FallbackMonitor` to centralize offline/fallback state and logs; minor runner/UI touchpoints.  
  - **Trade-offs**: Balanced complexity; introduces new module but keeps gateway lean.

## Effort & Risk
- **Effort**: M — multiple touchpoints (gateway, runner, UI, validation) but within current patterns.  
- **Risk**: Medium — threading/offline-state changes can impact gameplay responsiveness; validation tightening could reject more LLM outputs (must ensure fallback works).

## Recommendations / Research Needed
- Prefer **Option C**: add a small validator + fallback monitor to keep gateway lean while enforcing choice/effect rules and offline signaling; keep UI logging consistent.  
- Research: validate allowed resource names/items list for effects; decide log surface (UI vs file) and format; confirm acceptable choice count (always 2–3) and timeout duration.  
- Add deterministic tests for: choice count enforcement, catalog validation on effects, quota exhaustion → offline mode, timeout → UI log + fallback.***
