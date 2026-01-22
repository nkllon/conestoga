# Requirements Document

## Introduction
Conestoga is a scope-controlled, Oregon Trail-inspired journey simulation with a simple overland travel loop (grid-based travel, resources, party, inventory), where nearly all trail events are generated dynamically by the Gemini 3 API as structured, machine-actionable JSON. Events are historically grounded, responsive to game state (inventory, party, location, weather, time), and enforce deterministic rules (requirements, checks, effects) so the game remains stable, testable, and safe.

**API Version Requirement:** All Gemini API integrations MUST use Gemini 3 models exclusively. Preview APIs (e.g., `gemini-3-flash-preview`, `gemini-3-pro-preview`) are acceptable and encouraged for access to the latest features. Earlier model versions (Gemini 2.x, Gemini 1.x) are explicitly NOT supported.

The core "wow" is causal continuity: if the player acquires an item (e.g., shovel) through a Gemini-generated trade event, later Gemini-generated events can meaningfully reference it, but the game engine remains the source of truth for whether an interaction is possible.

Gemini is used to generate EventDrafts (narrative, options, requirements) and EventResolutions (outcomes, deltas, items, status changes) under strict schemas and validation loops.

## Goals
- Deliver a publicly accessible, no-login interactive demo that judges can run.
- Showcase Gemini 3 via a robust orchestrated event generation pipeline:
  - structured outputs (schema-constrained JSON)
  - deterministic validation and self-repair loop
  - stateful continuity (event history impacts future events)
  - **REQUIRED:** Use Gemini 3 models exclusively (preview APIs acceptable)
- Demonstrate Gemini 3 features as central to gameplay, including structured outputs, thinking controls, and safety settings.
- Keep gameplay scope intentionally minimal while ensuring high reliability and polish.

## Scope Boundaries
### In Scope (v1)
- Desktop game with a lightweight map, party stats, inventory, and time progression.
- Gemini-powered dynamic events and resolutions with strict JSON contracts.
- Save/load support for a run and a debug overlay for Gemini diagnostics.

## Non-Goals / Out of Scope
- Multiplayer, online accounts, payments, in-app purchases.
- Fully simulated 3D travel or complex combat systems.
- Medical/mental health diagnostic or treatment advice.
- Historically exhaustive simulation; focus is grounded feel and credible constraints.
- Baseline RAG chatbot where the app is primarily a prompt wrapper.
- Function calling as a dependency (optional for future iterations).

## Personas
- Player: Wants a fun, readable, replayable journey with meaningful choices.
- Hackathon Judge: Wants a working demo, clear Gemini integration, and a "wow" moment fast.
- Developer: Needs deterministic, testable rules around an LLM component.
- Content Curator: Wants historically grounded tone and respectful portrayal of peoples/cultures.

## Definitions / Glossary
- Event: A narrative scenario returned by Gemini as JSON containing choices, requirements, outcomes, and effects.
- Choice: A selectable player action, optionally gated by requirements.
- Requirement / Prerequisite: Machine-checkable condition on game state (e.g., has_item: shovel).
- Outcome: A result branch, optionally tied to an engine-resolved check (success/failure).
- Effect: A whitelisted state mutation (add/remove item, modify resource, set flag, etc.).
- Catalog: Canonical list of item IDs/resources/stats permitted in JSON responses.
- Validation / Repair Loop: Process where invalid event JSON is rejected with errors and regenerated.

## Requirements

### Requirement 1: Playable Core Loop (Travel -> Event -> Choice -> State Change)
**Objective:** As a player, I want a simple, repeatable journey loop, so that I can progress along the trail and experience consequential events.

#### Acceptance Criteria
1. When a new game starts, the Conestoga system shall initialize a valid game state (day, location, resources, party, inventory).
2. When the player advances travel by one step/turn, the Conestoga system shall update time and distance and evaluate whether an event triggers.
3. When an event is active, the Conestoga system shall present its narrative and a list of available choices.
4. When the player selects a choice, the Conestoga system shall apply deterministic outcomes and effects to the authoritative game state.
5. When win or lose conditions are met, the Conestoga system shall end the run and show a summary screen.

### Requirement 2: Simple Overland Map and Movement
**Objective:** As a player, I want a lightweight map (grid-based is acceptable), so that travel feels interactive without increasing scope.

#### Acceptance Criteria
1. When the player opens the map or travel view, the Conestoga system shall display the current position and nearby traversable tiles.
2. When the player moves to an adjacent tile, the Conestoga system shall advance time and update position.
3. If the target tile is not traversable, the Conestoga system shall prevent movement and provide feedback.
4. When movement occurs, the Conestoga system shall re-render within one frame without freezing the UI.

### Requirement 3: Authoritative Game State Model
**Objective:** As a developer, I want a well-defined, authoritative state model, so that LLM-driven content can be validated and executed safely.

#### Acceptance Criteria
1. When the game state is constructed, the Conestoga system shall include, at minimum: day, season, miles traveled or position, party health/morale/skills/status_conditions, resources (food, water, ammo, money), inventory, environment (biome, weather, terrain), run_history_summary, and flags.
2. When the game state is mutated, the Conestoga system shall enforce invariants (no negative resources, no negative inventory counts).
3. When the game requests an event from Gemini, the Conestoga system shall produce a compact, deterministic state summary derived from the authoritative state.
4. When the player opens a status screen, the Conestoga system shall display the authoritative state (not model text).

### Requirement 4: Inventory and Item Catalog (Canonical IDs)
**Objective:** As a developer, I want a canonical item catalog and IDs, so that event JSON references are stable and machine-actionable.

#### Acceptance Criteria
1. When the game starts, the Conestoga system shall load an item catalog with stable IDs (e.g., `itm_shovel`) and display names.
2. When an event references an item_id, the Conestoga system shall validate that it exists in the catalog.
3. If an event references an unknown item_id, the Conestoga system shall reject the event as invalid and attempt regeneration.
4. When inventory changes, the Conestoga system shall update the UI consistently within the same event resolution.
5. When an event introduces an emergent item, the Conestoga system shall normalize it into a stable item_id and store it in the catalog with tags usable for future prerequisites.
6. The Conestoga system shall maintain inventory as machine-checkable IDs and quantities for all items.

### Requirement 5: Gemini Event JSON Contract (Schema-Constrained Output)
**Objective:** As a developer, I want Gemini to return events as schema-valid JSON, so that the game can execute events deterministically.

#### Acceptance Criteria
1. When requesting a new event, the Conestoga system shall instruct Gemini to output only JSON conforming to the current event schema version.
2. When an event response is received, the Conestoga system shall validate it against the JSON schema before displaying it.
3. When schema validation succeeds, the Conestoga system shall treat the event as eligible for execution.
4. When schema validation fails, the Conestoga system shall follow the repair and fallback behavior in Requirement 9.
5. The Conestoga system shall define and enforce distinct schemas for EventDrafts (narrative/options/requirements) and EventResolutions (outcomes/deltas/status changes).
6. When a player selects a choice, the Conestoga system shall request an EventResolution using the selected option and authoritative state summary.

### Requirement 6: Event Content Must Be Interactable and State-Aware
**Objective:** As a player, I want events to acknowledge my inventory and party situation, so that choices feel meaningful and consistent.

#### Acceptance Criteria
1. When an event includes a choice with prerequisites, the Conestoga system shall evaluate prerequisites solely against authoritative state.
2. If prerequisites are not met, the Conestoga system shall hide or disable the choice and show a short reason (e.g., "Requires: Shovel").
3. When prerequisites are met, the Conestoga system shall allow the choice to be selected.
4. When an event proposes effects, the Conestoga system shall apply only whitelisted effect operations (see Requirement 8).

### Requirement 7: Deterministic Checks (Engine Rolls; LLM Suggests)
**Objective:** As a developer, I want deterministic resolution rules, so that outcomes are testable and fair.

#### Acceptance Criteria
1. When an event includes a check (e.g., skill check DC), the Conestoga system shall resolve success or failure using an engine-owned RNG.
2. When a check is resolved, the Conestoga system shall select the outcome branch (success or failure) as specified by the event JSON.
3. When a run is configured with a fixed seed, the Conestoga system shall produce repeatable check outcomes for identical choices.
4. If an event attempts to decide the outcome without providing a valid check structure, the Conestoga system shall treat the event as invalid or treat the outcome as unconditional according to validator policy.

### Requirement 8: Whitelisted Effects Only (Safe State Mutation)
**Objective:** As a developer, I want a whitelisted effect system, so that model outputs cannot perform unsafe operations.

#### Acceptance Criteria
1. When an event includes effects, the Conestoga system shall accept only a fixed whitelist (e.g., add_item, remove_item, modify_resource, modify_stat, set_flag, clear_flag, advance_time, damage_wagon, repair_wagon, log_journal, queue_followup).
2. If an event includes a non-whitelisted effect operation, the Conestoga system shall reject the event and attempt regeneration.
3. When applying effects, the Conestoga system shall enforce invariants (no negative resources, inventory bounds, stat bounds).
4. If effect application fails due to invariants, the Conestoga system shall abort event execution and revert to the pre-event state.

### Requirement 9: Validation + Self-Repair + Fallback (Reliability Layer)
**Objective:** As a hackathon judge, I want the demo to be reliable, so that the game keeps working even if the model outputs something invalid.

#### Acceptance Criteria
1. When an event fails schema validation, the Conestoga system shall request regeneration with a concise list of validation errors.
2. When regeneration is attempted, the Conestoga system shall limit attempts to a configured maximum (e.g., 2 to 3 retries).
3. If the maximum regeneration attempts are exceeded, the Conestoga system shall fall back to a local safe event deck that still uses the same JSON schema.
4. When a fallback event is used, the Conestoga system shall log that fallback occurred and continue the run normally.
5. If network or API errors occur, the Conestoga system shall use the same retry and fallback mechanism without freezing the UI.

### Requirement 10: Latency Management (Prefetch, Non-Blocking UI)
**Objective:** As a player, I want the game to remain responsive, so that event generation does not cause stutters or freezes.

#### Acceptance Criteria
1. When the game anticipates an event trigger, the Conestoga system shall prefetch the next event asynchronously without blocking rendering.
2. If an event is not ready when needed, the Conestoga system shall show a lightweight loading state without input lock beyond essential controls.
3. When the event arrives, the Conestoga system shall transition to the event UI without restarting the game loop.
4. When the game is running at target FPS, the Conestoga system shall maintain responsiveness while background calls are in progress.
5. When the player cancels event generation, the Conestoga system shall fall back to a deterministic offline event without stalling the UI.
6. The Conestoga system shall target 80 percent of event generations completing within 2.0 seconds on typical network conditions (best-effort).

### Requirement 11: Historical Grounding Mode (Without Turning Into Baseline RAG)
**Objective:** As a player, I want events to feel historically authentic, so that the journey is immersive and credible.

#### Acceptance Criteria
1. When requesting an event, the Conestoga system shall include constraints for time period, region, and material culture (tools, trade goods, landmarks) appropriate to the run context.
2. When the event includes provenance, the Conestoga system shall limit it to short paraphrased notes without long quotes.
3. If an event includes anachronistic content beyond allowed tolerance, the Conestoga system shall mark the event invalid and request regeneration.
4. When the run continues, the Conestoga system shall prefer continuity callbacks (previous decisions and flags) over random unrelated facts.

### Requirement 12: Cultural Respect and Content Safety Constraints
**Objective:** As a content curator, I want respectful portrayals and safe content, so that the demo avoids harmful stereotypes or disallowed content.

#### Acceptance Criteria
1. When generating events involving real peoples or cultures, the Conestoga system shall instruct the model to avoid stereotypes, slurs, and demeaning portrayals.
2. When the player encounters illness or injury content, the Conestoga system shall present it as game-state effects and narrative only, and shall not provide real-world diagnostic or treatment advice.
3. If the event content violates configured safety constraints, the Conestoga system shall reject it and request regeneration.
4. When a violation is detected repeatedly, the Conestoga system shall fall back to the safe local event deck.
5. The Conestoga system shall configure Gemini safety settings and internal guardrails to block sexual content, graphic violence, hate/harassment, and wrongdoing instructions.
6. The Conestoga system shall apply a local content filter (keyword blocklist and violence severity heuristic) before presenting model output.

### Requirement 13: Continuity and Follow-Up Events (Causal Chains)
**Objective:** As a player, I want earlier choices to matter later, so that the story feels coherent and reactive.

#### Acceptance Criteria
1. When an event queues a follow-up hint, the Conestoga system shall schedule it within an allowed window (earliest to latest).
2. When follow-up prerequisites are met, the Conestoga system shall increase the probability of triggering that follow-up.
3. When the follow-up triggers, the Conestoga system shall incorporate relevant prior flags and items into narrative and available choices.
4. If prerequisites are not met, the Conestoga system shall not present impossible interactions (e.g., "dig" without a shovel).

### Requirement 14: Run Persistence (Save/Load) and Session Continuity
**Objective:** As a player, I want to save and resume, so that longer runs are possible and demos are resilient.

#### Acceptance Criteria
1. When the player saves, the Conestoga system shall write the full authoritative state to a local save file.
2. When the player loads, the Conestoga system shall restore the authoritative state exactly and resume travel and event flow.
3. When saving, the Conestoga system shall include a bounded event history summary used for future event generation.
4. If a save file is corrupted or incompatible, the Conestoga system shall fail gracefully and allow starting a new run.

### Requirement 15: State Summary and Event History Packing Rules
**Objective:** As a developer, I want consistent prompt packing, so that Gemini receives stable context and continuity remains reliable.

#### Acceptance Criteria
1. When generating the state summary, the Conestoga system shall include only canonical fields and IDs (not UI text).
2. When including event history, the Conestoga system shall store and send a bounded summary (e.g., last N events and key flags) to avoid unbounded growth.
3. When the state summary changes, the Conestoga system shall reflect it deterministically for identical states.
4. When debugging is enabled, the Conestoga system shall display the state summary and last event IDs.

### Requirement 16: Gemini Model Configuration (Reasoning Depth by Tier)
**Objective:** As a developer, I want configurable model and reasoning depth, so that the system balances latency and quality.

#### Acceptance Criteria
1. When requesting a minor event, the Conestoga system shall use a low-latency configuration (model and reasoning depth) with reduced thinking controls.
2. When requesting a chapter event, the Conestoga system shall use a higher reasoning configuration.
3. When configuration is changed, the Conestoga system shall apply it to subsequent generation calls without code changes.
4. If the model is unavailable, the Conestoga system shall fall back to the safe local deck (Requirement 9).

### Requirement 17: Secure API Key Handling
**Objective:** As a developer, I want safe key handling, so that the public demo does not leak credentials.

#### Acceptance Criteria
1. When the application starts, the Conestoga system shall load the Gemini API key from environment variables or a non-committed config file.
2. When running in any public or demo mode, the Conestoga system shall not hardcode keys in the repository or client-side bundles.
3. When logging requests or responses, the Conestoga system shall redact secrets.
4. If the key is missing, the Conestoga system shall run in offline or fallback mode with clear messaging.

### Requirement 18: Observability (Logs, Artifacts, Debug Overlay)
**Objective:** As a hackathon judge, I want to understand how Gemini is used, so that the integration is obvious and credible.

#### Acceptance Criteria
1. When an event is generated, the Conestoga system shall record an event artifact containing event_id, tier, validation status, and chosen outcome.
2. When validation fails, the Conestoga system shall log the failure reasons and regeneration attempts.
3. When debug mode is enabled, the Conestoga system shall show current day or mile, inventory highlights, last event_id, request id, latency, and token counts when available.
4. Where the model provides thought summaries and debug mode is enabled, the Conestoga system shall display them in a developer-only view.
5. When exporting a run summary, the Conestoga system shall produce a shareable artifact (JSON or text) without secrets.

### Requirement 19: Public Demo Packaging (No Login, Judge-Friendly)
**Objective:** As a hackathon judge, I want frictionless access, so that I can try the project immediately.

#### Acceptance Criteria
1. When the public demo link is opened, the Conestoga system shall allow interactive use without requiring login or payment.
2. When the demo is started, the Conestoga system shall reach a playable state within a short, defined time budget (e.g., under 15 seconds on typical hardware).
3. If the demo environment cannot access Gemini, the Conestoga system shall still be playable via fallback mode.
4. When the demo ends, the Conestoga system shall provide a clear restart or new-run path.

### Requirement 20: Hackathon Submission Deliverables Embedded in the Project
**Objective:** As a developer, I want submission requirements baked into the repo, so that we can ship confidently and consistently.

#### Acceptance Criteria
1. When preparing the submission, the Conestoga system shall include an approximately 200-word "Gemini Integration" description that explains Gemini features used and why they are central.
2. When preparing the submission, the Conestoga system shall include a roughly 3-minute demo video script or shot list that demonstrates the key loop (generate -> validate -> interact -> state impacts future event).
3. When preparing the submission, the Conestoga system shall include an architecture diagram (static image or Mermaid) that explains components and data flow.
4. When the repository is published, the Conestoga system shall include run instructions for local execution and demo mode configuration.

### Requirement 21: Automated Testing for Core Determinism and Safety
**Objective:** As a developer, I want automated tests, so that changes do not break determinism, validation, or safety.

#### Acceptance Criteria
1. When running unit tests, the Conestoga system shall validate schema validation, prerequisite evaluation, effect application, and invariant enforcement.
2. When running integration tests, the Conestoga system shall run with mocked Gemini responses (golden fixtures) to ensure reproducibility.
3. When invalid event fixtures are provided, the Conestoga system shall confirm the repair loop behavior (retry then fallback).
4. When tests complete, the Conestoga system shall report coverage for critical modules (validator, state, effects engine).

### Requirement 22: Minimal UX Polish (Readability and Controls)
**Objective:** As a player, I want readable events and simple controls, so that gameplay is smooth and understandable.

#### Acceptance Criteria
1. When an event is displayed, the Conestoga system shall present narrative text in readable line lengths and paginate if needed.
2. When choices are displayed, the Conestoga system shall label them clearly and indicate locked requirements.
3. When the player navigates screens, the Conestoga system shall provide consistent keybindings and visible hints.
4. When the game encounters an error state, the Conestoga system shall show a friendly message and recover where possible.

## Priority Legend
- P0: Must-have for a stable hackathon demo and judging success.
- P1: Strongly recommended; improves wow-factor, reliability, or clarity.
- P2: Nice-to-have; only if time allows.

By default, Requirements 1 to 10, 12, 17, 19, and 20 are P0. The rest are P1 or P2 depending on team capacity.

