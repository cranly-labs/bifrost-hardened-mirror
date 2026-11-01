#!/usr/bin/env bash
# Build-independent smoke test for the distribution image.
set -euo pipefail

IMAGE="${IMAGE:-bifrost-distribution:smoke}"
PORT="${PORT:-18080}"
VERSION="${BIFROST_VERSION:-}"
CONTAINER="bifrost-smoke-$$"
VOLUME="bifrost-smoke-$$"
HEALTH_FILE="$(mktemp)"
VERSION_FILE="$(mktemp)"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker volume rm "$VOLUME" >/dev/null 2>&1 || true
  rm -f "$HEALTH_FILE" "$VERSION_FILE"
}
trap cleanup EXIT

docker volume create "$VOLUME" >/dev/null
docker run -d \
  --name "$CONTAINER" \
  -p "127.0.0.1:${PORT}:8080" \
  -v "${VOLUME}:/app/data" \
  -e BIFROST_SETUP_TOKEN="smoke-test-token" \
  -e LOG_LEVEL="info" \
  -e LOG_STYLE="json" \
  "$IMAGE" >/dev/null

ready=0
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; then
    break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  echo "error: gateway did not become healthy" >&2
  docker logs "$CONTAINER" >&2 || true
  exit 1
fi

curl -fsS "http://127.0.0.1:${PORT}/health" > "$HEALTH_FILE"
curl -fsS "http://127.0.0.1:${PORT}/api/version" > "$VERSION_FILE"

if [ -n "$VERSION" ]; then
  if ! grep -q "$VERSION" "$VERSION_FILE"; then
    echo "error: /api/version does not report ${VERSION}" >&2
    cat "$VERSION_FILE" >&2
    exit 1
  fi
fi

uid="$(docker exec "$CONTAINER" id -u)"
if [ "$uid" = "0" ]; then
  echo "error: container is running as root" >&2
  exit 1
fi

echo "smoke test passed: health=OK version=$(cat "$VERSION_FILE") uid=${uid}"
