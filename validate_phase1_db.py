#!/usr/bin/env python
"""
Minimal Database Validation Script.

Tests database schema without heavy dependencies.
"""

import os
import sys

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Set SQLite for testing
os.environ['DATABASE_URL'] = 'sqlite:///./data/test_database.db'

print("="*60)
print("Phase 1 & 2 Database Validation")
print("="*60)
print()
print("Database:", os.environ['DATABASE_URL'])
print()

# Create data directory
os.makedirs('./data', exist_ok=True)

try:
    # Import SQLAlchemy directly
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    # Create our own Base and engine (avoiding package imports)
    Base = declarative_base()
    engine = create_engine(os.environ['DATABASE_URL'], echo=False)

    # Import ONLY the model files directly (not through package)
    sys.path.insert(0, 'src/networking_ai')
    print("Importing Phase 1 models...")
    import models.user
    import models.personal_ai_agent
    import models.agent_conversation
    import models.interview_session
    import models.sub_agent_activation
    import models.user_knowledge
    import models.network_knowledge
    import models.audit_log
    print("✅ All Phase 1 models imported")

    print("Importing Phase 2 models...")
    import models.company_admin_agent
    import models.hiring_manager_role
    import models.company_admin_user
    import models.subscription
    print("✅ All Phase 2 models imported\n")

    # Create tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created\n")

    # Inspect database
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"Found {len(tables)} tables:")
    for table in sorted(tables):
        print(f"  ✓ {table}")
    print()

    # Check Phase 1 & 2 critical tables
    critical_tables = [
        # Phase 1
        'users',
        'personal_ai_agents',
        'agent_conversations',
        'interview_sessions',
        'sub_agent_activations',
        'user_knowledge',
        'network_knowledge',
        'audit_logs',
        # Phase 2
        'company_admin_agents',
        'hiring_manager_roles',
        'company_admin_users',
        'subscriptions'
    ]

    print("Validating Phase 1 & 2 critical tables:")
    all_present = True
    for table in critical_tables:
        if table in tables:
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} MISSING")
            all_present = False
    print()

    if all_present:
        print("="*60)
        print("✅ PHASE 1 & 2 DATABASE VALIDATION PASSED")
        print("="*60)
        print()
        print("All critical tables present and schema is valid.")
        print("Ready for testing with proper environment setup.")
        sys.exit(0)
    else:
        print("❌ Some tables missing - schema issues detected")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
