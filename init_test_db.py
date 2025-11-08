#!/usr/bin/env python
"""Simple database initialization for testing."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Set simpler DATABASE_URL for testing
os.environ['DATABASE_URL'] = 'sqlite:///./data/test_database.db'

print("Initializing test database...")
print(f"Database: {os.environ['DATABASE_URL']}")
print()

# Now import database module
try:
    # Import database module directly (before main package)
    import networking_ai.database as db_module

    # Import all model modules to register tables
    print("Importing models...")
    import networking_ai.models.user
    import networking_ai.models.profile
    import networking_ai.models.company
    import networking_ai.models.job
    import networking_ai.models.application
    import networking_ai.models.match
    import networking_ai.models.message
    import networking_ai.models.ai_agent
    import networking_ai.models.personal_ai_agent
    import networking_ai.models.agent_conversation
    import networking_ai.models.interview_session
    import networking_ai.models.sub_agent_activation
    import networking_ai.models.user_knowledge
    import networking_ai.models.network_knowledge
    import networking_ai.models.audit_log

    print("✅ Models imported\n")

    # Create tables
    print("Creating tables...")
    db_module.Base.metadata.create_all(bind=db_module.engine)

    print("✅ Database initialized!")
    print()
    print("Tables created:")
    for table in sorted(db_module.Base.metadata.tables.keys()):
        print(f"  - {table}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTrying minimal sentence_transformers install...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', 'sentence-transformers'],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Retrying...")
    # Retry after install
    import networking_ai.database as db_module
    db_module.Base.metadata.create_all(bind=db_module.engine)
    print("✅ Database initialized!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
