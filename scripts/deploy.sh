#!/usr/bin/env bash
# PRISM — Manual deploy helper (run on the server)
# Usage: bash scripts/deploy.sh [IMAGE_TAG]
#   IMAGE_TAG defaults to 'production'
set -euo pipefail

IMAGE_TAG="${1:-production}"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=== PRISM Deploy ==="
echo "IMAGE_TAG: $IMAGE_TAG"
echo ""

# Verify .env exists
if [[ ! -f ".env" ]]; then
    echo "ERROR: .env not found. Run scripts/server-setup.sh first."
    exit 1
fi

# Verify DOMAIN is set
source .env
if [[ -z "${DOMAIN:-}" ]]; then
    echo "ERROR: DOMAIN is not set in .env"
    exit 1
fi

# Pull new images
echo "Pulling images..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" pull backend worker frontend

# Start/update services
echo "Starting services..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" up -d

# Wait for backend health
echo "Waiting for backend..."
for i in {1..30}; do
    if curl -sf "https://${DOMAIN}/api/health" > /dev/null 2>&1; then
        echo "Backend healthy."
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "ERROR: Backend did not become healthy after 30s"
        docker compose -f "$COMPOSE_FILE" logs --tail=50 backend
        exit 1
    fi
    sleep 2
done

# Prune old images
docker image prune -f

echo ""
echo "=== Deploy complete ==="
echo "Site: https://${DOMAIN}"
echo "Logs: docker compose -f $COMPOSE_FILE logs -f"
