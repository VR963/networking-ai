#!/bin/bash
# Run tests inside Docker container

echo "🧪 Running Tests Inside Docker Container"
echo "========================================"
echo ""

# Check if app container is running
if ! docker ps | grep -q networking-ai-app; then
    echo "❌ Error: networking-ai-app container is not running"
    echo "Run: docker compose up -d"
    exit 1
fi

# Run pytest inside the container
echo "Running pytest..."
docker compose exec -T app pytest "$@"

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
