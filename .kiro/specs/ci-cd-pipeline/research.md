# Research

## Summary
- Full discovery executed for new CI/CD pipeline to enforce reproducible Python 3.12 builds, deterministic headless testing, and gated releases aligned with Conestoga's steering.
- Pipeline will center on GitHub Actions with uv-based builds, ruff linting, pytest in headless mode, secret/vulnerability scanning, and artifact packaging/gating.
- Template `.kiro/settings/templates/specs/research.md` is missing; fallback structure used to capture findings and decisions.

## Discovery Scope
- Requirements coverage: 1.1-1.3 (triggers), 2.1-2.4 (build reproducibility), 3.1-3.4 (quality gates), 4.1-4.3 (security/compliance), 5.1-5.6 (release/promotion).
- Non-functional drivers: reproducibility, traceability, security of secrets, deterministic tests, artifact integrity, deployment gating/rollback safety.

## Research Log
- Pipeline orchestration: No existing CI directory; assume GitHub Actions as default for GitHub-hosted repos to satisfy trigger requirements (1.x). Alternatives considered: GitLab CI, Jenkins; Actions chosen for lower overhead and repo integration.
- Build toolchain: Makefile uses `uv sync`, `uv run pytest`, `uv run ruff`; lockfile `uv.lock` present. Build target runtime Python 3.12 (req 2.4). Use uv cache to speed builds; ensure lockfile validation (2.1-2.3).
- Testing/quality: Tests via `uv run pytest`; headless enforced by `CI`/`UI_HEADLESS` envs per steering (3.1, 3.4). Lint via `uv run ruff check .` (3.3). Need artifacted test reports for PR feedback (1.2, 3.2).
- Security/compliance: Plan secret scanning (e.g., gitleaks) and dependency vulnerability scanning (e.g., pip-audit) with fail-on-high severity (4.1, 4.2). Log redaction for secrets in CI output (4.3).
- Release and promotion: Use `uv build` (wheel/sdist) plus zipped assets for Pygame resources; attach checksums and store as workflow artifacts (5.1, 5.2). Deployment gate validates secrets like `GEMINI_API_KEY` before promoting (5.4-5.5). Rollback job blocks concurrent deploys (5.6).
- External research: No external web search performed due to offline environment; recommendations rely on standard CI/CD practices and repository conventions.

## Architecture Pattern Evaluation
- Considered centralized CI orchestrator with staged jobs vs monolithic script. Chose staged GitHub Actions workflow with dependent jobs (build → test → scan → release → deploy gate) to enforce gating and parallelize where safe. Alternative: containerized Jenkins pipeline; rejected for added infra overhead.

## Design Decisions (detailed in design doc)
- Orchestrator: GitHub Actions with matrix for Python 3.12 only initially.
- Artifact strategy: uv wheel/sdist + assets bundle with SHA256; stored as workflow artifacts.
- Security controls: gitleaks for secrets, pip-audit for dependencies, log redaction filters in CI steps.

## Risks and Mitigations
- Runner environment missing Pygame/system libs → use headless mode, install minimal deps, and skip rendering-reliant tests; document prerequisites.
- Cache poisoning or stale deps → validate against `uv.lock`, refresh cache on hash change.
- Secrets handling → mark secrets as masked, avoid echoing; enforce required secrets check before deploy.
- Artifact bloat → prune retention, compress assets, and checksum before upload.

## Open Questions
- Deployment target/platform not defined; need environment-specific deploy script and rollback hooks.
- Desired artifact retention period and storage backend (Actions artifacts vs external bucket) pending product decision.
- Which branches/tags constitute release channels (e.g., `main`, `release/*`, `v*` tags) to be confirmed.
