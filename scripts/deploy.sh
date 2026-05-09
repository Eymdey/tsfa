#!/bin/bash
set -e

echo "=== TSFA Deploy ==="

echo "Pulling latest code..."
git pull origin main

echo "Building new image..."
docker-compose build --no-cache api

echo "Running tests..."
docker-compose run --rm api pytest tests/ -x -q

echo "Deploying..."
docker-compose up -d --force-recreate api

echo "Waiting for health check..."
sleep 5
curl -f http://localhost:8000/health || (echo "Health check failed!" && exit 1)

echo "=== Deploy complete ==="
