#!/usr/bin/env bash
# Usage:
#   ./deploy.sh            → build, push to Docker Hub, redeploy Azure
#   ./deploy.sh 1.0.1      → same but also tags :1.0.1

set -euo pipefail

IMAGE="vishalsingh2003/mlabapi"
TAG="${1:-}"
AZURE_APP_NAME="mlabapi"
AZURE_RESOURCE_GROUP="container-app"

# ── 1. Build & push to Docker Hub ─────────────────────────────
echo "🔨 Building $IMAGE:latest (linux/amd64 + linux/arm64)..."

TAGS="-t $IMAGE:latest"
if [ -n "$TAG" ]; then
  TAGS="$TAGS -t $IMAGE:$TAG"
fi

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f mlabapi/Dockerfile \
  $TAGS \
  --push \
  .

echo "✅ Pushed $IMAGE:latest${TAG:+ and $IMAGE:$TAG} to Docker Hub"

# ── 2. Force Azure to pull the new image ──────────────────────
echo "🚀 Redeploying Azure Container App '$AZURE_APP_NAME'..."

az containerapp update \
  --name "$AZURE_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --image "$IMAGE:latest"

echo "✅ Azure Container App '$AZURE_APP_NAME' updated to $IMAGE:latest"
