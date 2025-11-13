#!/bin/bash
# Script to cleanly rebuild Docker images and run tests

echo "=== Cleaning up Python cache files ==="
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo "=== Stopping and removing containers ==="
docker compose down -v

echo "=== Building Docker images (no cache) ==="
docker compose build --no-cache

echo "=== Starting services ==="
docker compose up -d

echo "=== Waiting for services to be healthy ==="
sleep 15

echo "=== Running tests ==="
docker compose exec app python -m pytest tests/test_core.py -v

echo "=== Done! ==="
echo "To run all tests: docker compose exec app pytest -v"
echo "To view logs: docker compose logs -f app"
