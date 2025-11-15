# Database Setup and Management

This document explains how to set up and manage the database for the Networking AI platform.

## Overview

The application supports two database backends:
- **PostgreSQL** (recommended for production)
- **SQLite** (for local development and testing)

The database is automatically initialized when the Docker container starts, creating all necessary tables based on SQLAlchemy models.

## Automatic Database Initialization

When you start the application with Docker Compose, the database tables are automatically created on first startup:

```bash
docker-compose up --build
```

The initialization process:
1. Waits for PostgreSQL to be ready
2. Runs `init_db.py` to create all tables
3. Starts the FastAPI application

## Manual Database Initialization

If you need to manually initialize the database (e.g., for local development), you can run:

```bash
# Set the DATABASE_URL environment variable
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/networking_ai"

# Run the initialization script
python init_db.py
```

For SQLite (local development):
```bash
# SQLite is the default if DATABASE_URL is not set
python init_db.py
```

## Database Configuration

### Docker Environment

The database is configured via environment variables in `docker-compose.yml`:

```yaml
DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

Default values (can be overridden in `.env` file):
- `POSTGRES_DB=networking_ai`
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_PORT=5432`

### Local Development

For local development without Docker, set the `DATABASE_URL` environment variable:

**PostgreSQL:**
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
```

**SQLite (default):**
```bash
# No environment variable needed - SQLite is the default
# Or explicitly set:
export DATABASE_URL="sqlite:///./data/networking_ai.db"
```

## Verifying Database Initialization

After the application starts, you can verify that tables were created:

### Using Docker:
```bash
# Access the PostgreSQL container
docker exec -it networking-ai-postgres psql -U postgres -d networking_ai

# List all tables
\dt

# Exit
\q
```

### Expected Tables:

The database should contain approximately 50+ tables for all platform features:

Core tables:
- `users` - User accounts
- `user_profiles` - User profile information
- `companies` - Company information
- `jobs` - Job postings
- `applications` - Job applications
- `matches` - AI-powered matches
- `conversations` - Messaging conversations
- `messages` - Individual messages

Agent system tables:
- `personal_ai_agents` - Personal AI assistants
- `company_admin_agents` - Company AI agents
- `agent_conversations` - Agent conversation history
- `interview_sessions` - AI interview sessions
- `user_knowledge` - User knowledge base
- `network_knowledge` - Network-wide knowledge

And many more for subscriptions, billing, notifications, analytics, etc.

## Resetting the Database

### Docker Environment:

To completely reset the database:

```bash
# Stop all containers
docker-compose down

# Remove the PostgreSQL volume (THIS DELETES ALL DATA!)
docker volume rm networking-ai-postgres-data

# Start fresh
docker-compose up --build
```

### Local Development:

For SQLite:
```bash
# Delete the database file
rm -f data/networking_ai.db

# Re-initialize
python init_db.py
```

For PostgreSQL:
```bash
# Drop and recreate the database
psql -U postgres -c "DROP DATABASE IF EXISTS networking_ai;"
psql -U postgres -c "CREATE DATABASE networking_ai;"

# Re-initialize
python init_db.py
```

## Troubleshooting

### Tables Not Created

If tables are not being created automatically:

1. **Check the logs:**
   ```bash
   docker-compose logs app
   ```
   Look for database initialization messages.

2. **Manually run initialization inside container:**
   ```bash
   docker exec -it networking-ai-app python init_db.py
   ```

3. **Verify PostgreSQL is accessible:**
   ```bash
   docker exec -it networking-ai-app pg_isready -h postgres -p 5432
   ```

### Connection Errors

If you see connection errors:

1. **Ensure PostgreSQL is running:**
   ```bash
   docker-compose ps postgres
   ```

2. **Check PostgreSQL logs:**
   ```bash
   docker-compose logs postgres
   ```

3. **Verify network connectivity:**
   ```bash
   docker exec -it networking-ai-app ping postgres
   ```

### Permission Errors

If you encounter permission errors:

1. **Check volume permissions:**
   ```bash
   ls -la data/
   ```

2. **Fix ownership (if needed):**
   ```bash
   sudo chown -R 1000:1000 data/
   ```

## Migration Strategy (Future)

For production deployments, it's recommended to use **Alembic** for database migrations instead of the simple `create_all()` approach. This allows for:

- Version-controlled schema changes
- Reversible migrations
- Safe production deployments

The current implementation uses `Base.metadata.create_all()` for simplicity during development.

## Backup and Restore

### Backup:

```bash
# Using Docker
docker exec networking-ai-postgres pg_dump -U postgres networking_ai > backup.sql

# Or using docker-compose
docker-compose exec postgres pg_dump -U postgres networking_ai > backup.sql
```

### Restore:

```bash
# Using Docker
docker exec -i networking-ai-postgres psql -U postgres networking_ai < backup.sql

# Or using docker-compose
docker-compose exec -T postgres psql -U postgres networking_ai < backup.sql
```

## Security Notes

1. **Change default passwords** in production!
2. Use **strong passwords** for PostgreSQL
3. Store credentials in **environment variables** or secure vaults
4. Never commit `.env` files with real credentials
5. Use **SSL/TLS** for database connections in production

## References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/) (for future migrations)
