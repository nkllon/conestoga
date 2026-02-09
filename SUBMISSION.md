# Devpost Submission Details

## Project Info

**Project Name:** Conestoga
**Tagline:** An Oregon Trail-inspired journey simulation with Gemini 3 API dynamic events, built with modern Python tooling.

## Project Description

**The Problem**
Procedural generation in games often feels generic or nonsensical. We wanted to harness the power of LLMs like Gemini 3 to create rich, context-aware narratives in a classic journey simulation ("Oregon Trail" style) without sacrificing game balance, safety, or determinism.

**The Solution**
Conestoga is a desktop journey simulation where the Gemini 3 API (specifically `gemini-3-flash-preview`) acts as a dynamic "Dungeon Master". It generates structured `EventDrafts` and `EventResolutions` based on the player's current state (biome, inventory, party health).

Critically, the game engine enforces a strict separation between the "Authoritative Simulation" (deterministic rules) and the "Narrative Generation" (LLM). All Gemini outputs are validated against strict schemas, safety filters, and game logic invariants before being presented to the player.

**How we built it**

- **Core Engine:** Python 3.12+ with `pygame-ce` for the UI.
- **AI Integration:** `google-genai` SDK targeting `gemini-3-flash-preview` for low-latency event generation.
- **Architecture:** A "Hexagonal" architecture that isolates the core domain logic from external services (AI, persistence).
- **Data & Safety:** `pydantic` v2 for rigorous schema validation and `rdflib` for ontology-based data management.
- **Tooling:** `uv` for modern package management.

**Challenges we ran into**

- Ensuring the LLM outputs were not just creative but *game-legal* (e.g., not granting impossible items). We solved this with a robust validation pipeline that can reject and retry invalid generations.
- Balancing latency with richness. We use asynchronous pre-fetching and `flash` models to keep the UI responsive.

**Accomplishments that we're proud of**

- A fully playable, deterministic loop where every run feels unique but fair.
- Seamless integration of Gemini 3 features in a desktop app context.
- A "Fallback Monitor" that ensures the game remains playable even if the API is offline (using a local deck of events).

**What's next for Conestoga**

- Expanding the ontology to support more diverse biomes and granular events.
- Integrating `gemini-3-pro-preview` for deeper "chapter" level narrative arcs.

---

## Demo Video Script

**Target Length:** ~2 minutes
**Assets Available:**

- `screenshots/oregon_trail_map.png`
- `assets/conestoga loop - travel - *.mp4` (various biomes)

| Time | Visual | Audio (Voiceover) |
| :--- | :--- | :--- |
| **0:00-0:15** | **Image:** `oregon_trail_map.png` (Pan/Zoom) | "Welcome to Conestoga, a modern reimagining of the classic journey simulation, powered by the new Gemini 3 API." |
| **0:15-0:30** | **Clip:** `conestoga loop - travel - blue mountains.mp4` | "In Conestoga, you lead a party across a perilous landscape. But unlike traditional games, the events you face aren't just random database entries." |
| **0:30-0:50** | **Clip:** `conestoga loop - travel - kansas crossings.mp4` | "We use Gemini 3 Flash to generate context-aware scenarios in real-time. The AI considers your party's health, inventory, and location to craft unique narrative moments." |
| **0:50-1:10** | **Clip:** `conestoga loop - travel - rocky mountains.mp4` | "Crucially, we maintain strict determinism. The game engine validates every AI response against a rigorous schema. If Gemini suggests an invalid action, our validation pipeline catches it before it breaks the game." |
| **1:10-1:30** | **Clip:** `conestoga loop - travel - western plains.mp4` | "This means you get the infinite creativity of a Large Language Model with the reliability and balance of a handcrafted RPG. The UI remains responsive thanks to asynchronous pre-fetching." |
| **1:30-1:50** | **Clip:** `conestoga loop - travel - eastern plains.mp4` | "Built with Python 3.12, Pygame-CE, and Pydantic, Conestoga demonstrates how to integrate advanced AI into robust desktop applications safely and effectively." |
| **1:50-2:00** | **Clip:** `conestoga loop - travel - oregon.mp4` | "Survive the journey. Experience the story. This is Conestoga." |
