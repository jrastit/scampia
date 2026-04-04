#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-up}"

if docker compose version >/dev/null 2>&1; then
	COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
	COMPOSE_CMD=(docker-compose)
else
	echo "Docker Compose not found. Install docker compose plugin or docker-compose."
	exit 1
fi

case "${ACTION}" in
	up)
		"${COMPOSE_CMD[@]}" up -d --build
		;;
	down)
		"${COMPOSE_CMD[@]}" down
		;;
	logs)
		"${COMPOSE_CMD[@]}" logs -f scampia
		;;
	restart)
		"${COMPOSE_CMD[@]}" down
		"${COMPOSE_CMD[@]}" up -d --build
		;;
	*)
		echo "Usage: $0 [up|down|logs|restart]"
		exit 1
		;;
esac
