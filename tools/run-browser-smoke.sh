#!/bin/sh

set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
port=${E2E_PORT:-4173}
image_name=heat-chronicle-browser-smoke
container_name=heat-chronicle-browser-smoke-$$

cleanup() {
  docker rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker build -f "$repository_root/frontend/Dockerfile.prod" -t "$image_name" "$repository_root/frontend"
docker run --rm -d --name "$container_name" -p "127.0.0.1:$port:80" "$image_name" >/dev/null

attempt=0
until curl -fsS "http://127.0.0.1:$port/" >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    docker logs "$container_name"
    exit 1
  fi
  sleep 1
done

cd "$repository_root/frontend"
E2E_BASE_URL="http://127.0.0.1:$port" npm run test:e2e
