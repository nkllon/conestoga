# Conestoga Executive Summary

## Vision

Conestoga is an AI-driven reinvention of the classic "Oregon Trail" journey simulation, designed to demonstrate the capabilities of Gemini 3. It combines a nostalgic, deterministic gameplay loop with dynamic, LLM-generated narrative events, creating a unique and replayable experience that showcases the potential of modern AI in gaming.

## Business Value

- **Showcase Gemini 3**: Demonstrates advanced AI capabilities such as structured JSON generation, long-context understanding, and creative writing in a constrained environment.
- **Resilience & Reliability**: Proves that AI-integrated applications can be robust, featuring offline fallbacks, graceful degradation, and deterministic state management even when the AI is unavailable.
- **Engaging User Experience**: Offers a compelling, high-fidelity browser-based experience with modern aesthetics, bridging the gap between tech demo and playable game.

## Key Features

- **Dynamic Event Engine**: procedurally generated narrative events that adapt to the player's current state (party health, inventory, location).
- **Structured Intelligence**: Uses Gemini's schema validation to ensure AI outputs are always game-compatible (e.g., valid choices, resource impacts).
- **Hybrid Architecture**: A Python/Pygame core for deterministic logic and a Gemini integration layer for creative content.
- **Web-Native & Cloud-Ready**: Deployed on Google Cloud Run for scalability and accessibility, with a modern web frontend.

## Roadmap

1. **Phase 1: Prototype (Completed)** - Core game loop, basic Pygame UI, initial Gemini connection.
2. **Phase 2: Resilience (Current)** - Offline fallback deck, retry logic, structured logging, 1Password integration.
3. **Phase 3: Polish & Deployment (Next)** - Enhanced visual assets, mobile responsiveness, public launch on custom domain (`conestoga.nkllon.com`).
4. **Phase 4: Expansion (Future)** - persistent leaderboards, social sharing of "journey logs", deeper narrative branches.
