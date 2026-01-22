# Research & Design Decisions

## Summary
- **Feature**: conestoga
- **Discovery Scope**: New Feature
- **Key Findings**:
  - The design should use a layered architecture with a dedicated LLM integration boundary to protect deterministic simulation and enable safe fallback paths.
  - Gemini SDK behavior and feature availability (structured outputs, thinking controls, safety settings) must be verified against official documentation during implementation due to evolving preview APIs.
  - Desktop-first runtime favors local file persistence and background worker threads to avoid UI blocking under network latency.

## Research Log

### Gemini SDK capabilities and constraints
- **Context**: Requirements demand structured outputs, thinking controls, and safety settings in production calls.
- **Sources Consulted**:
  - Web search for official Gemini SDK documentation and API references (results returned generic or non-authoritative content).
- **Findings**:
  - Official documentation and SDK references were not reliably retrieved via search in this environment.
  - Implementation must validate SDK method names, configuration objects, and supported models from the official Gemini documentation at build time.
- **Implications**:
  - Design includes explicit interface boundaries and configuration objects but defers exact SDK signatures to implementation verification.
  - Risk logged for SDK version drift and preview endpoint changes.

### Python desktop stack selection
- **Context**: Requirements specify a desktop Python game with non-blocking UI.
- **Sources Consulted**:
  - Web search for Pygame-CE, Python 3.11 compatibility, and Pydantic v2 usage (results not authoritative).
- **Findings**:
  - Desktop Python stack remains appropriate; UI threading and background network calls are required to meet latency and responsiveness requirements.
- **Implications**:
  - Design uses a single-threaded render loop with an asynchronous worker for Gemini calls and deterministic game simulation on the main thread.

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Layered Monolith | UI, application services, domain simulation, infrastructure in-process | Simple deployment, easy debugging | Risk of tight coupling without clear boundaries | Baseline for desktop game |
| Hexagonal (Ports & Adapters) | Core domain isolated behind ports; adapters for Gemini, persistence, UI | Strong testability, clear LLM boundary | Additional interface design overhead | Selected for LLM safety and determinism |
| Event-driven | Asynchronous event bus between subsystems | Scales if future web demo or services | Overkill for single-process desktop | Deferred unless web demo expands |

## Design Decisions

### Decision: Layered core with hexagonal boundaries
- **Context**: LLM integration must not corrupt authoritative state or block UI.
- **Alternatives Considered**:
  1. Layered monolith without explicit ports
  2. Hexagonal core with adapters for Gemini and persistence
- **Selected Approach**: Layered architecture with explicit ports for Gemini generation, validation, and persistence.
- **Rationale**: Keeps deterministic logic isolated, supports offline fallback, and allows strict validation gates.
- **Trade-offs**: Requires more upfront interface definition and mapping between DTOs and domain objects.
- **Follow-up**: Confirm exact Gemini SDK interfaces during implementation.

### Decision: Background worker for Gemini calls
- **Context**: UI must remain responsive during network latency.
- **Alternatives Considered**:
  1. Synchronous calls on main loop
  2. Dedicated background worker with polling
- **Selected Approach**: Single background worker to serialize Gemini calls and simplify cancellation/fallback behavior.
- **Rationale**: Prevents UI freezes and ensures deterministic ordering of event requests.
- **Trade-offs**: Requires explicit state transitions and request lifecycle management.
- **Follow-up**: Validate thread safety of shared state access.

### Decision: Data-driven content packs with schema versioning
- **Context**: The game must expand routes, landmarks, and events without code changes.
- **Alternatives Considered**:
  1. Hardcoded content in source files
  2. External content packs with schema validation
- **Selected Approach**: Content packs stored as versioned JSON or YAML with stable IDs and strict schema validation.
- **Rationale**: Enables rapid iteration, mod-like expansion, and safe LLM event authoring.
- **Trade-offs**: Requires upfront schema definition and migration handling.
- **Follow-up**: Define schema versions and migration rules in implementation.

### Decision: LLM event authoring pipeline with balance gating
- **Context**: LLM-generated events must not destabilize simulation balance.
- **Alternatives Considered**:
  1. Full LLM event creation with minimal checks
  2. Flavor-only generation by default with optional full authoring
- **Selected Approach**: Two-mode pipeline with schema validation, safety checks, and balance scoring.
- **Rationale**: Preserves deterministic gameplay while enabling new content.
- **Trade-offs**: Additional validation complexity and content curation overhead.
- **Follow-up**: Calibrate severity thresholds per difficulty tier.

## Risks & Mitigations
- Gemini SDK or model changes break structured output or thinking controls — Mitigate with pinned dependency and a validation harness.
- Latency spikes exceed 2.0s target — Mitigate with prefetch, cancel-to-fallback, and short prompt summaries.
- Safety filters over-block legitimate content — Mitigate with layered filters and logging for tuning.
- LLM-generated events introduce imbalance — Mitigate with balance scoring, gating, and flavor-only default mode.

## References
- [Gemini API Docs](https://ai.google.dev/) — Official Gemini documentation entry point (verify SDK specifics)
- [Google GenAI SDK (Python)](https://github.com/googleapis/python-genai) — SDK repository for signatures and examples
- [Pygame-CE](https://github.com/pygame-community/pygame-ce) — Desktop UI framework option
- [Pydantic](https://docs.pydantic.dev/) — Schema validation for structured outputs
