#!/bin/sh
set -eu
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image_name=${BACKEND_DEV_IMAGE:-heat-chronicle-backend-dev-smoke}
port=${BACKEND_SMOKE_PORT:-18080}
network_name=heat-backend-smoke-$$
db_name=heat-backend-db-$$
app_name=heat-backend-app-$$
cleanup() {
  docker rm -f "$app_name" "$db_name" >/dev/null 2>&1 || true
  docker network rm "$network_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker build --platform linux/amd64 -f "$repository_root/backend/Dockerfile" -t "$image_name" "$repository_root/backend"
docker network create "$network_name" >/dev/null
docker run --rm -d --name "$db_name" --network "$network_name" --network-alias dynamodb-local   amazon/dynamodb-local:latest -jar DynamoDBLocal.jar -inMemory -sharedDb >/dev/null
docker run --rm -d --platform linux/amd64 --name "$app_name" --network "$network_name"   -p "127.0.0.1:$port:8000" -e DYNAMODB_ENDPOINT_URL=http://dynamodb-local:8000   -e DYNAMODB_TABLE_PREFIX=dev-image-smoke "$image_name" >/dev/null
attempt=0
until curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 90 ]; then
    docker logs "$app_name"
    exit 1
  fi
  sleep 1
done
for path in /health /api/prefectures/ '/api/stations/?prec_no=44' /api/temperature/4; do
  curl -fsS "http://127.0.0.1:$port$path" >/dev/null
done
docker exec "$app_name" python -c 'import sys, importlib.util; assert sys.version_info[:2] == (3,14); assert importlib.util.find_spec("poetry") is None; assert importlib.util.find_spec("pytest") is not None'
echo 'Development image: Python 3.14, initialization, seed and four API routes passed'
