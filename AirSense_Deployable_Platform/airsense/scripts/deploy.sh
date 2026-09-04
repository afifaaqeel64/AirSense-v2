#!/bin/bash
# Production deployment script
set -e
echo "Deploying AirSense to production..."

# Pull latest
git pull origin main

# Build & restart services with zero downtime
docker-compose -f docker-compose.yml pull
docker-compose -f docker-compose.yml up -d --build --no-deps api celery-worker celery-beat
docker-compose -f docker-compose.yml up -d frontend nginx

# Wait for API to be healthy
echo "Waiting for API health check..."
for i in {1..30}; do
  if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✓ API is healthy"
    break
  fi
  sleep 5
done

docker system prune -f --volumes=false
echo "✓ Deployment complete"
