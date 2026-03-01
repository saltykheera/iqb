#!/usr/bin/env bash
# Usage:
#   ./deploy.sh            → build, push to Docker Hub, redeploy Azure
#   ./deploy.sh 1.0.1      → same but also tags :1.0.1

set -euo pipefail

IMAGE="vishalsingh2003/mlabapi"
TAG="${1:-}"
AZURE_APP_NAME="mlabapi"
AZURE_RESOURCE_GROUP="container-app"

# Timestamp tag so Azure always pulls a genuinely new image (never stale cache)
DEPLOY_TAG="$(date -u +%Y%m%d-%H%M%S)"

# ── 1. Build & push to Docker Hub ─────────────────────────────
echo "🔨 Building $IMAGE:$DEPLOY_TAG (linux/amd64 + linux/arm64)..."

TAGS="-t $IMAGE:latest -t $IMAGE:$DEPLOY_TAG"
if [ -n "$TAG" ]; then
  TAGS="$TAGS -t $IMAGE:$TAG"
fi

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f mlabapi/Dockerfile \
  $TAGS \
  --push \
  .

echo "✅ Pushed $IMAGE:latest and $IMAGE:$DEPLOY_TAG to Docker Hub"

# ── 2. Force Azure to pull the new image ──────────────────────
# Using the timestamped tag (not :latest) so Azure detects a real image change
echo "🚀 Redeploying Azure Container App '$AZURE_APP_NAME' → image tag :$DEPLOY_TAG ..."

az containerapp update \
  --name "$AZURE_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --image "$IMAGE:$DEPLOY_TAG"

echo "✅ Azure Container App '$AZURE_APP_NAME' updated to $IMAGE:$DEPLOY_TAG"
