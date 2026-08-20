#!/usr/bin/env bash
# Local MQTT integration + ping/pong against Docker Compose EMQX.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/tests${PYTHONPATH:+:$PYTHONPATH}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
  export PATH="$ROOT/.venv/bin:$PATH"
else
  PYTHON="${PYTHON:-python3}"
fi

COMPOSE="${MQTT_COMPOSE:-docker compose -f docker-compose.yml -f docker-compose.dev.yml}"
export MQTT_COMPOSE="$COMPOSE"
export PLATFORM_URL="${PLATFORM_URL:-http://127.0.0.1:8000}"
export MQTT_HOST="${MQTT_HOST:-127.0.0.1}"
export MQTT_PORT="${MQTT_PORT:-8883}"
export MQTT_CA_FILE="${MQTT_CA_FILE:-$ROOT/certs/ca.crt}"
export MQTT_ALLOW_BROKER_RESTART="${MQTT_ALLOW_BROKER_RESTART:-1}"

test -f .env || cp .env.example .env
test -f certs/server.crt || ./scripts/generate-local-mqtt-certs.sh

echo "==> Starting postgres, redis, backend, emqx"
BUILD_ARGS=()
if [[ "${MQTT_COMPOSE_BUILD:-}" == "1" ]]; then
  BUILD_ARGS+=(--build)
fi
# shellcheck disable=SC2086
if ! $COMPOSE up -d "${BUILD_ARGS[@]}" --wait --wait-timeout 180 postgres redis backend emqx; then
  echo "==> Compose --wait unavailable; starting without --wait"
  # shellcheck disable=SC2086
  $COMPOSE up -d "${BUILD_ARGS[@]}" postgres redis backend emqx
fi

cleanup() {
  if [[ "${MQTT_COMPOSE_DOWN:-}" == "1" ]]; then
    echo "==> Stopping Compose services"
    # shellcheck disable=SC2086
    $COMPOSE down
  fi
}
trap cleanup EXIT

echo "==> Waiting for backend and MQTT TLS"
"$PYTHON" - <<'PY'
from mqtt_live.config import load_config
from mqtt_live.http import wait_http, wait_mqtt_tls

cfg = load_config()
wait_http(f"{cfg.platform_url}/health", timeout_seconds=180)
wait_mqtt_tls(cfg.mqtt_host, cfg.mqtt_port, cfg.mqtt_ca_file, timeout_seconds=180)
print("backend and MQTT TLS are ready")
PY

echo "==> MQTT integration + ping/pong"
"$PYTHON" -m pytest -q tests/mqtt_live
echo "==> MQTT tests passed"
