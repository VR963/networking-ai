#!/bin/sh
set -e

echo "=================================="
echo "Networking AI Platform - Starting"
echo "=================================="

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "^postgresql://"; then
    echo "Waiting for PostgreSQL to be ready..."

    # Extract database connection info from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's#.*@\([^:]*\):.*#\1#p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's#.*:\([0-9]*\)/.*#\1#p')

    # Default to standard PostgreSQL port if extraction failed
    DB_HOST="${DB_HOST:-postgres}"
    DB_PORT="${DB_PORT:-5432}"

    echo "Checking PostgreSQL at $DB_HOST:$DB_PORT"

    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
            echo "✅ PostgreSQL is ready"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Waiting for PostgreSQL... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "❌ PostgreSQL is not available after $MAX_RETRIES attempts"
        exit 1
    fi
else
    echo "Using SQLite database (no PostgreSQL wait needed)"
fi

# Initialize database tables
echo ""
echo "Initializing database tables..."
python init_db.py

if [ $? -ne 0 ]; then
    echo "❌ Database initialization failed"
    exit 1
fi

echo ""
echo "=================================="
echo "Starting FastAPI application..."
echo "=================================="
echo ""

# Execute the main command
exec "$@"
