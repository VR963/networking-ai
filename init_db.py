#!/usr/bin/env python
"""
Database initialization script for PostgreSQL.

This script creates all database tables using SQLAlchemy models.
It can be run manually or as part of the deployment process.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("DATABASE INITIALIZATION")
print("=" * 80)
print()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/networking_ai.db')
print(f"Database URL: {DATABASE_URL}")
print()

# Import database module
try:
    from networking_ai.database import Base, engine

    # Import all models to ensure they're registered with SQLAlchemy
    # This is critical - models must be imported before create_all()
    print("Importing all models...")
    import networking_ai.models  # This imports all models from __init__.py

    print(f"✅ Successfully imported {len(Base.metadata.tables)} model(s)")
    print()

    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    print("✅ All tables created successfully!")
    print()

    # List all created tables
    print("Tables in database:")
    for i, table_name in enumerate(sorted(Base.metadata.tables.keys()), 1):
        print(f"  {i:2d}. {table_name}")

    print()
    print("=" * 80)
    print("DATABASE INITIALIZATION COMPLETE")
    print("=" * 80)

except Exception as e:
    print(f"❌ Error initializing database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
