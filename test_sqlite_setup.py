#!/usr/bin/env python3
"""
Quick test to verify SQLite database setup works.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from networking_ai.database import engine, Base, init_db, DATABASE_URL
# Import models to register them with SQLAlchemy
import networking_ai.models


def test_sqlite_setup():
    """Test that SQLite database can be initialized."""
    print("=" * 60)
    print("Testing SQLite Database Setup")
    print("=" * 60)

    print(f"\n1. Database URL: {DATABASE_URL}")

    if not DATABASE_URL.startswith('sqlite'):
        print("\n❌ ERROR: Not using SQLite!")
        print("   Please check your .env file")
        return False

    print("✓ Using SQLite database")

    print("\n2. Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"❌ ERROR creating tables: {e}")
        return False

    print("\n3. Checking database file...")
    db_path = DATABASE_URL.replace('sqlite:///', '')
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path)
        print(f"✓ Database file created: {db_path}")
        print(f"  File size: {file_size:,} bytes")
    else:
        print(f"❌ Database file not found: {db_path}")
        return False

    print("\n4. Testing database connection...")
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Connected successfully")
        print(f"  Tables found: {len(tables)}")
        for table in sorted(tables):
            print(f"    - {table}")
    except Exception as e:
        print(f"❌ ERROR connecting to database: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ SQLite Setup Complete!")
    print("=" * 60)
    print("\nYou can now run the application with:")
    print("  python -m uvicorn networking_ai.api.main:app --reload")
    print("\nOr use the demo app:")
    print("  python demo_app.py")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_sqlite_setup()
    sys.exit(0 if success else 1)
