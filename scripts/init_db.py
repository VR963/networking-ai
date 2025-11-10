#!/usr/bin/env python
"""
Database Initialization Script.

Creates all database tables for Phase 1 testing.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.networking_ai.database import Base, engine, init_db
from src.networking_ai import models  # Import all models


def main():
    """Initialize database with all tables."""
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)
    print()

    # Check database URL
    db_url = os.getenv('DATABASE_URL', 'Not set')
    print(f"Database URL: {db_url}")
    print()

    try:
        # Create all tables
        print("Creating database tables...")
        init_db()
        print()
        print("✅ Database initialized successfully!")
        print()

        # List all tables
        print("Tables created:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")
        print()

        return 0

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
