# Conestoga System Architecture

## Overview

Conestoga is built as a hybrid application: a deterministic Python game engine combined with a stochastic AI generation layer.

## Context Diagram (C4 Context)

```mermaid
graph TD
    User((Player))
    subgraph "Conestoga System"
        GameApp[Conestoga Application]
        GeminiAPI[Google Gemini 3 API]
        CloudRun[Google Cloud Run]
    end
    User -->|Plays via Browser/CLI| GameApp
    GameApp -->|Requests Event Drafts| GeminiAPI
    GameApp -->|Hosted on| CloudRun
```

## Component Architecture

```mermaid
classDiagram
    class GameRunner {
        +start()
        +game_loop()
    }
    class EventService {
        +prefetch_next_event()
        +get_current_event()
    }
    class GeminiGateway {
        +generate_content(prompt)
        +validate_response(schema)
    }
    class GameState {
        inventory: Dict
        party: List
        update(effects)
    }
    class UI {
        +render_scene()
        +get_input()
    }

    GameRunner --> GameState
    GameRunner --> EventService
    GameRunner --> UI
    EventService --> GeminiGateway
    EventService ..> GameState : Reads context
```

## Critical Flows

### Event Generation (Prefetch)

This sequence runs in a background thread while the player is travelling.

```mermaid
sequenceDiagram
    participant Game as Game Loop
    participant Service as EventService
    participant Gateway as GeminiGateway
    participant API as Gemini API

    Game->>Service: prefetch_next_event()
    Service->>Gateway: create_prompt(current_state)
    Gateway->>API: generate_content()
    API-->>Gateway: JSON Response
    Gateway->>Gateway: validate_schema(EventDraft)
    Gateway-->>Service: Validated Event
    Service-->>Game: Event Ready
```

### Event Resolution

When a player makes a choice.

```mermaid
sequenceDiagram
    participant UI
    participant Game as Game Loop
    participant State as GameState

    UI->>Game: select_choice(index)
    Game->>State: apply_effects(choice.effects)
    State-->>Game: Updated State (Health, Items)
    Game->>UI: show_resolution(text)
    Game->>Game: transition_to(TRAVELLING)
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> LOADING
    LOADING --> TRAVEL : Assets Loaded
    TRAVEL --> EVENT : Random Trigger OR Planned
    EVENT --> RESOLUTION : Player Choice
    RESOLUTION --> TRAVEL : Continue Journey
    RESOLUTION --> GAME_OVER : Party Health <= 0
    GAME_OVER --> [*]
```
