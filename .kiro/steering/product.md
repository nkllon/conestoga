# Product
- **Purpose**: Oregon Trail-inspired journey sim that demonstrates Gemini 3-driven dynamic events with schema validation and deterministic state updates.
- **Player Experience**: Travel-loop pacing with periodic narrative events, 2-3 choice resolutions, resource and morale tradeoffs, and a fallback deck when LLM calls are offline or throttled.
- **Value**: Showcases resilient Gemini 3 integration (prefetching, validation, graceful degradation) plus a playable Pygame prototype suitable for demos and research on AI-generated game content.
- **Core Loops**: Travel → event trigger → choice → resolution → inventory/state update; async prefetch keeps the UI responsive and hides LLM latency.

