#!/usr/bin/env bash
set -euo pipefail

# Configurable knobs
RUN_DOCKER=${RUN_DOCKER:-0}                          # 1 to start compose services
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.test.yml}
TEST_RUN_DIR=${TEST_RUN_DIR:-/tmp/conestoga-tests/$USER-run}

mkdir -p "$TEST_RUN_DIR"
echo "[test-pre] Using temp dir: $TEST_RUN_DIR"

if [[ "$RUN_DOCKER" == "1" ]]; then
  if [[ -f "$COMPOSE_FILE" ]]; then
    echo "[test-pre] Starting services via $COMPOSE_FILE"
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
  else
    echo "[test-pre] Skipping Docker start; compose file not found: $COMPOSE_FILE"
  fi
else
  echo "[test-pre] RUN_DOCKER=0; not starting services"
fi

echo "[test-pre] Ready for tests"
