#!/usr/bin/env bash
set -euo pipefail

RUN_DOCKER=${RUN_DOCKER:-0}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.test.yml}
TEST_RUN_DIR=${TEST_RUN_DIR:-/tmp/conestoga-tests/$USER-run}

if [[ "$RUN_DOCKER" == "1" ]]; then
  if [[ -f "$COMPOSE_FILE" ]]; then
    echo "[test-post] Tearing down services via $COMPOSE_FILE"
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
  else
    echo "[test-post] Skip teardown; compose file not found: $COMPOSE_FILE"
  fi
else
  echo "[test-post] RUN_DOCKER=0; no services to stop"
fi

if [[ -d "$TEST_RUN_DIR" ]]; then
  echo "[test-post] Cleaning temp dir: $TEST_RUN_DIR"
  rm -rf "$TEST_RUN_DIR"
else
  echo "[test-post] Temp dir not present: $TEST_RUN_DIR"
fi

echo "[test-post] Cleanup complete"
