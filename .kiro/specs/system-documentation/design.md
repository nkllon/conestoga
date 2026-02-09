# System Documentation Design

## Documentation Structure

The documentation will be organized in a flattened `docs/` directory for simplicity, linked from `README.md`.

### Files

1. **`docs/executive_summary.md`**:
    - **Purpose**: High-level overview for stakeholders.
    - **Content**: Project vision, business value (AI-driven narrative), roadmap, key features.
2. **`docs/architecture.md`**:
    - **Purpose**: Technical deep-dive for architects and senior devs.
    - **Content**:
        - System Context Diagram (Mermaid C4 Context).
        - Container Diagram (Mermaid C4 Container).
        - Component Diagram (Python modules).
        - Detailed Sequence Diagrams (Voyage loop, Event Draft, Resolution).
        - State Diagram (Game States).
3. **`docs/devops.md`**:
    - **Purpose**: Deployment and operations manual.
    - **Content**:
        - Deployment to Cloud Run (gcloud/console steps).
        - CI/CD Pipelines (GitHub Actions for build/test/lint).
        - Secrets Management (1Password integration).
        - Monitoring (Log Explorer).
4. **`docs/developer.md`**:
    - **Purpose**: Guide for contributors.
    - **Content**:
        - Setup (`uv` environment, dependencies).
        - Project Structure (`src/`, `tests/`, `scripts/`).
        - Testing Strategy (`pytest`, Docker Compose).
        - Contribution Workflow (PRs, linters).
5. **`README.md` (Update)**:
    - Add "Documentation" section linking to the above files.

## Diagrams (Mermaid)

- **Context**: User -> Conestoga (Web/CLI) -> Gemini 3 API.
- **Sequence**:
    1. `Game.travel()` triggers `EventService.prefetch()`.
    2. `EventService` calls `GeminiGateway`.
    3. `GeminiGateway` returns structured JSON.
    4. `EventService` validates via `EventDraft` schema.
    5. UI renders event.
- **State**: `TRAVEL` -> `EVENT` -> `CHOICE` -> `RESOLUTION` -> `INVENTORY` -> `TRAVEL`.
