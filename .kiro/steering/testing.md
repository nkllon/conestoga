# Testing
- **Required scope**: Unit tests for new/changed code paths; favor deterministic checks (seed randomness, fixed fixtures) over mocking to validate real behavior.
- **Doubles**: Avoid mocks/stubs unless isolating nondeterministic third-party calls; prefer lightweight fakes or test data that exercise validation paths.
- **Execution**: Run with `uv run pytest` (Make target: `make test`); keep tests self-contained and parallel-safe.
- **Environment**: Shared workspace—use temp dirs and unique resource names; spin up external dependencies via Docker when needed and tear them down after the run.
- **Setup/teardown**: Provide explicit pre-test scripts to provision prerequisites (e.g., `docker compose up <service> -d`) and post-test scripts to clean temp services/artifacts; fail fast if setup cannot complete.
- **Audits**: When heuristic audits are triggered, use LangChain to wrap/abstract the chosen LLM for test review; capture findings as actionable notes without blocking normal test runs.
- **Scripts**: Use `scripts/test-pre.sh` and `scripts/test-post.sh` to prepare/clean environments; set `RUN_DOCKER=1` and `COMPOSE_FILE=docker-compose.test.yml` (or your file) to manage services, and set `TEST_RUN_DIR` to isolate temp data in shared environments.
- **Compose stub**: `docker-compose.test.yml` ships with Redis, Postgres, and MinIO examples; trim services you don’t need and override credentials/ports per environment before running.
