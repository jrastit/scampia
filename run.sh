#!/usr/bin/env bash
set -euo pipefail

export NETWORK="${NETWORK:-ethereum-sepolia}"
export APP_HOST="${APP_HOST:-127.0.0.1}"
export APP_PORT="${APP_PORT:-8000}"
export APP_ROOT_PATH="${APP_ROOT_PATH:-/api}"
export APP_RELOAD="${APP_RELOAD:-false}"

UVICORN_ARGS=(
	app.main:app
	--host "${APP_HOST}"
	--port "${APP_PORT}"
	--proxy-headers
	--forwarded-allow-ips "*"
)

if [[ "${APP_RELOAD,,}" == "1" || "${APP_RELOAD,,}" == "true" || "${APP_RELOAD,,}" == "yes" || "${APP_RELOAD,,}" == "on" ]]; then
	UVICORN_ARGS+=(--reload)
fi

exec uvicorn "${UVICORN_ARGS[@]}"