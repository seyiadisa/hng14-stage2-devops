#!/usr/bin/env bash
set -euo pipefail

NETWORK_NAME="${NETWORK_NAME:-deploy-net}"
REDIS_CONTAINER_NAME="${REDIS_CONTAINER_NAME:-deploy-redis}"
OLD_CONTAINER_NAME="${OLD_CONTAINER_NAME:-api-old}"
NEW_CONTAINER_NAME="${NEW_CONTAINER_NAME:-api-candidate}"
LIVE_CONTAINER_NAME="${LIVE_CONTAINER_NAME:-api-live}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:7.2-alpine}"
OLD_IMAGE="${OLD_IMAGE:?OLD_IMAGE is required}"
NEW_IMAGE="${NEW_IMAGE:?NEW_IMAGE is required}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-60}"

wait_for_health() {
  local container_name="$1"
  local timeout_seconds="$2"
  local start_time
  start_time="$(date +%s)"

  while true; do
    local health_status
    health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_name}")"

    if [[ "${health_status}" == "healthy" ]]; then
      return 0
    fi

    if [[ "${health_status}" == "unhealthy" ]]; then
      return 1
    fi

    if (( "$(date +%s)" - start_time >= timeout_seconds )); then
      return 1
    fi

    sleep 2
  done
}

docker network create "${NETWORK_NAME}" >/dev/null 2>&1 || true

docker run -d \
  --name "${REDIS_CONTAINER_NAME}" \
  --network "${NETWORK_NAME}" \
  --health-cmd "redis-cli ping" \
  --health-interval 5s \
  --health-timeout 3s \
  --health-retries 12 \
  "${REDIS_IMAGE}" >/dev/null

wait_for_health "${REDIS_CONTAINER_NAME}" "${HEALTH_TIMEOUT_SECONDS}"

docker run -d \
  --name "${OLD_CONTAINER_NAME}" \
  --network "${NETWORK_NAME}" \
  -e REDIS_HOST="${REDIS_CONTAINER_NAME}" \
  -e REDIS_PORT=6379 \
  -e API_PORT=8000 \
  "${OLD_IMAGE}" >/dev/null

wait_for_health "${OLD_CONTAINER_NAME}" "${HEALTH_TIMEOUT_SECONDS}"

docker run -d \
  --name "${NEW_CONTAINER_NAME}" \
  --network "${NETWORK_NAME}" \
  -e REDIS_HOST="${REDIS_CONTAINER_NAME}" \
  -e REDIS_PORT=6379 \
  -e API_PORT=8000 \
  "${NEW_IMAGE}" >/dev/null

if ! wait_for_health "${NEW_CONTAINER_NAME}" "${HEALTH_TIMEOUT_SECONDS}"; then
  echo "New container failed health checks within ${HEALTH_TIMEOUT_SECONDS} seconds. Leaving old container running."
  docker logs "${NEW_CONTAINER_NAME}" || true
  docker rm -f "${NEW_CONTAINER_NAME}" >/dev/null 2>&1 || true
  exit 1
fi

docker stop "${OLD_CONTAINER_NAME}" >/dev/null
docker rm "${OLD_CONTAINER_NAME}" >/dev/null
docker rename "${NEW_CONTAINER_NAME}" "${LIVE_CONTAINER_NAME}"
echo "Rolling deployment succeeded. ${LIVE_CONTAINER_NAME} is healthy."
