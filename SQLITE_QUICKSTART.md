# Quick Start with SQLite

The application now uses **SQLite** by default for easy local development - no Docker or PostgreSQL needed!

## What Changed

- **Database**: Switched from PostgreSQL to SQLite
- **No Docker Required**: Run the app directly on your machine
- **Faster Setup**: Get started in minutes, not hours

## How to Run

### 1. Set Up Environment

Copy and edit the `.env` file:

```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

The database is already configured to use SQLite by default:
```
DATABASE_URL=sqlite:///./data/networking_ai.db
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test Database Setup

```bash
python test_sqlite_setup.py
```

You should see:
```
✅ SQLite Setup Complete!
Tables found: 85
```

### 4. Run the Application

```bash
python -m uvicorn networking_ai.api.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the demo app:
```bash
python demo_app.py
```

### 5. Access the Application

- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/health
- **Landing Page**: http://localhost:8000/

## Database File Location

The SQLite database is stored at:
```
./data/networking_ai.db
```

## Switching to PostgreSQL (Production)

When you're ready for production with PostgreSQL:

1. Update your `.env` file:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/networking_ai
```

2. Start PostgreSQL (via Docker):
```bash
docker-compose up -d postgres
```

The application will automatically detect and use PostgreSQL instead of SQLite.

## Troubleshooting

### Database File Not Found
If you get database errors, ensure the `data/` directory exists:
```bash
mkdir -p data
```

### Tables Not Created
Run the test script to verify setup:
```bash
python test_sqlite_setup.py
```

### Port Already in Use
If port 8000 is busy, use a different port:
```bash
python -m uvicorn networking_ai.api.main:app --reload --port 8001
```

## Benefits of SQLite for Development

- ✅ No Docker containers needed
- ✅ No PostgreSQL installation required
- ✅ Single file database (easy to backup/delete)
- ✅ Perfect for testing and development
- ✅ Fast setup (<5 minutes)
- ✅ Portable across different machines

## Next Steps

1. Set your `ANTHROPIC_API_KEY` in `.env`
2. Run the test script to verify setup
3. Start the application
4. Visit the API docs at `/api/docs`
5. Start building!
