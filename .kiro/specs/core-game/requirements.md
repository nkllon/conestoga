# Requirements Document

## Introduction
Core Conestoga gameplay loop: travel pacing, Gemini-driven narrative events with deterministic state updates, and resilient fallback behavior when LLM calls are unavailable.

## Requirements

### Requirement 1: Travel Loop and Progression
**Objective:** As a player, I want a predictable travel loop that advances the journey and surfaces events at trail milestones so that the game feels paced and responsive.

#### Acceptance Criteria
1. WHEN the game starts THEN the Core Game SHALL initialize day counter, miles traveled, party, and inventory using the catalog defaults.
2. WHILE the game is in TRAVEL mode THE Core Game SHALL advance days and miles and evaluate event trigger probability each tick.
3. WHEN an event trigger occurs THEN the Core Game SHALL pause travel progression and transition to EVENT or LOADING mode.
4. WHERE the travel log is displayed THE Game UI SHALL show current day, miles progress, and party status after each tick or event.

### Requirement 2: Event Generation and Resilience
**Objective:** As a player, I want each event to be generated from trail context with a reliable fallback so that the story continues even if Gemini is offline.

#### Acceptance Criteria
1. WHEN an event trigger occurs THEN the Gemini Gateway SHALL request an event draft from a Gemini 3 model using current game state.
2. IF the Gemini response is unavailable, times out, or fails schema validation THEN the Core Game SHALL supply an event from the fallback deck.
3. WHEN an event is presented THEN it SHALL include at least two and no more than three unique player choices with clear text and prerequisites.
4. WHERE API quota exhaustion is detected THE Gemini Gateway SHALL mark Gemini offline for the session and route future event requests to the fallback deck.

### Requirement 3: Choice Resolution and State Effects
**Objective:** As a player, I want each choice to produce consistent narrative outcomes and state changes so that decisions feel consequential and fair.

#### Acceptance Criteria
1. WHEN a player selects a choice THEN the Core Game SHALL validate availability against prerequisites before executing it.
2. IF a choice is valid THEN the Resolution Engine SHALL produce a resolution (via Gemini or fallback) and apply its effects to resources, inventory, and party stats.
3. WHEN an effect references an inventory item THEN the Resolution Engine SHALL confirm the item exists in the catalog before adding or removing it.
4. WHEN a resolution completes THEN the Game UI SHALL log the narrative outcome and updated resource totals.

### Requirement 4: UI Feedback and Responsiveness
**Objective:** As a player, I want clear feedback during loading, event presentation, and resolutions so that I always know what the game is doing.

#### Acceptance Criteria
1. WHEN the game is fetching an event or resolution THEN the Game UI SHALL display a loading indicator until content is ready or a timeout elapses.
2. IF event generation exceeds the configured timeout THEN the Core Game SHALL fall back to a cached or deck event and inform the player via the log.
3. WHERE event choices are rendered THE Game UI SHALL highlight the current selection and disable unavailable options with a reason.
4. WHEN resources or inventory change THEN the Game UI SHALL reflect the new values before returning to TRAVEL mode.

### Requirement 5: Observability and Recovery
**Objective:** As a maintainer, I want diagnostics around LLM calls and fallback behavior so that issues can be identified and the game remains playable.

#### Acceptance Criteria
1. WHEN a Gemini call fails or is rejected THEN the Gemini Gateway SHALL record the failure reason and set a flag indicating fallback usage for that request.
2. IF repeated failures occur in a session THEN the Core Game SHALL switch to fallback-only mode to avoid blocking gameplay.
3. WHERE fallback content is used THE Core Game SHALL note the source (prefetched vs deck) in logs visible to maintainers for troubleshooting.


