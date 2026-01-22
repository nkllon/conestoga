---
name: conestoga-sdd-ontology
description: Use for spec-driven development assets (requirements/design/tasks) and ontology/SHACL traceability in the Conestoga repo. Covers .kiro specs/steering, ontology/conestoga.ttl, and audit hooks.
---

# Conestoga SDD & Ontology Skill

## Spec/Steering Layout
- Specs: `.kiro/specs/core-game/` (`requirements.md`, `design.md`, `tasks.md`, `gap-analysis.md`, `research.md`, `spec.json`).
- Steering: `.kiro/steering/` (`product.md`, `tech.md`, `structure.md`, `testing.md`).
- Templates/Rules: `.kiro/settings/templates/specs/`, `.kiro/settings/rules/` (EARS, design/gap/task rules).

## Workflow Reminders
- Follow phase order: requirements → design → tasks → implementation.
- Requirements/design/tasks approval flags live in `spec.json` (update when generating).
- Task list in `tasks.md` stays traceable to requirement IDs; update checkboxes cautiously.

## Ontology & Audits
- Ontology: `ontology/conestoga.ttl` (requirements/components/tasks/tests/impl links) with SHACL shapes for requirements coverage.
- SHACL check (optional): `uv run pytest tests/test_ontology.py` (needs pyshacl).
- Heuristic audits: `src/conestoga/game/audit.py` (`HEURISTIC_AUDIT=1`, optional LangChain chain `default_langchain_chain`).

## Testing & Headless
- CI defaults headless (`UI_HEADLESS`/`CI`); set `UI_HEADLESS=0` to view UI locally.
- Tests: `uv run pytest` (UI, validation, audit, ontology).

## Traceability
- Map requirement IDs from `requirements.md` in design traceability and ontology.
- Components: validator, fallback monitor, Gemini gateway, runner, UI recorded in ontology.
