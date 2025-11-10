#!/usr/bin/env python
"""
Standalone Database Initialization Script.

Creates all database tables without importing the full application.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create base
Base = declarative_base()

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/test_database.db')

print("=" * 60)
print("Database Initialization")
print("=" * 60)
print()
print(f"Database URL: {DATABASE_URL}")
print()

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Import all models (this registers them with Base)
print("Importing models...")

from networking_ai.models.user import User
from networking_ai.models.profile import UserProfile
from networking_ai.models.company import Company
from networking_ai.models.job import Job
from networking_ai.models.application import Application
from networking_ai.models.match import Match
from networking_ai.models.message import Conversation, Message
from networking_ai.models.ai_agent import AIAgent

# New agent marketplace models (Phase 1)
from networking_ai.models.personal_ai_agent import PersonalAIAgent
from networking_ai.models.agent_conversation import AgentConversation
from networking_ai.models.interview_session import InterviewSession
from networking_ai.models.sub_agent_activation import SubAgentActivation
from networking_ai.models.user_knowledge import UserKnowledge
from networking_ai.models.network_knowledge import NetworkKnowledge
from networking_ai.models.audit_log import AuditLog

# Phase 2: Company & Subscription Models
from networking_ai.models.company_admin_agent import CompanyAdminAgent
from networking_ai.models.hiring_manager_role import HiringManagerRole
from networking_ai.models.company_admin_user import CompanyAdminUser
from networking_ai.models.subscription import Subscription

print("✅ Models imported")
print()

# Create all tables
print("Creating database tables...")
try:
    # Update Base.metadata to use the imported models' metadata
    from networking_ai.database import Base as AppBase
    AppBase.metadata.create_all(bind=engine)

    print()
    print("✅ Database initialized successfully!")
    print()

    # List all tables
    print("Tables created:")
    for table in AppBase.metadata.sorted_tables:
        print(f"  - {table.name}")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
