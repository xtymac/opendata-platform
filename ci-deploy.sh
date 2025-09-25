#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$REPO_DIR"

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
CKAN_SERVICE=${CKAN_SERVICE:-ckan}
CKAN_CONTAINER=${CKAN_CONTAINER_NAME:-yamaguchi-ckan}
log() {
  printf '%s\n' "[deploy] $*"
}

log "Pulling latest images"
docker compose -f "$COMPOSE_FILE" pull

log "Starting services"
docker compose -f "$COMPOSE_FILE" up -d

wait_for_service() {
  local name=$1
  local retries=${2:-30}
  local delay=${3:-10}
  local status

  for _ in $(seq 1 "$retries"); do
    status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || echo 'not-found')
    case "$status" in
      healthy|running)
        return 0
        ;;
      not-found)
        log "Container $name not found yet; waiting"
        ;;
      created|starting)
        log "Container $name starting..."
        ;;
      exited|dead)
        log "Container $name status: $status"
        return 1
        ;;
      *)
        log "Container $name health: $status"
        ;;
    esac
    sleep "$delay"
  done
  log "Timed out waiting for $name to become healthy"
  return 1
}

log "Waiting for ${CKAN_CONTAINER} to become healthy"
wait_for_service "$CKAN_CONTAINER" 36 5

CKAN_INI_PATH=${CKAN_INI_PATH:-/srv/app/ckan.ini}
log "Running database migrations"
docker compose -f "$COMPOSE_FILE" exec -T "$CKAN_SERVICE" sh -c "ckan -c $CKAN_INI_PATH db upgrade"

log "Deployment completed"
