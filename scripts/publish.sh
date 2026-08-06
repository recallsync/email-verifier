#!/usr/bin/env bash
# Build and push Email Verifier images to Docker Hub.
#
# Prerequisites:
#   docker login
#
# Usage:
#   ./scripts/publish.sh              # push :latest and :postgres-16
#   ./scripts/publish.sh v1.0.0       # also push version tag
#   VERSION=v1.0.0 ./scripts/publish.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

IMAGE="${DOCKER_IMAGE:-envisiontechai/fusionsyncai-email-verifier}"
VERSION="$(cat VERSION 2>/dev/null || echo "latest")"
TAG="${1:-}"

echo "==> Building app image..."
docker build -t "${IMAGE}:latest" .

echo "==> Building postgres image..."
docker build -t "${IMAGE}:postgres-16" ./postgres

echo "==> Pushing ${IMAGE}:latest"
docker push "${IMAGE}:latest"

echo "==> Pushing ${IMAGE}:postgres-16"
docker push "${IMAGE}:postgres-16"

if [[ -n "$TAG" ]]; then
  echo "==> Tagging and pushing version: ${TAG}"
  docker tag "${IMAGE}:latest" "${IMAGE}:${TAG}"
  docker tag "${IMAGE}:postgres-16" "${IMAGE}:postgres-${TAG}"
  docker push "${IMAGE}:${TAG}"
  docker push "${IMAGE}:postgres-${TAG}"
fi

echo ""
echo "Done. Images published:"
echo "  ${IMAGE}:latest          (app)"
echo "  ${IMAGE}:postgres-16    (postgres + pg_cron)"
[[ -n "$TAG" ]] && echo "  ${IMAGE}:${TAG} / ${IMAGE}:postgres-${TAG}"
