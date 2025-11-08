# Phase 2 Week 2 - Multi-User Architecture Implementation

## Overview

Phase 2 Week 2 implements the **multi-user architecture** with support for:
- **Talent** (job seekers) - Free for 12 months
- **Hiring Managers** (company employees) - Company seat-based
- **Recruiters** (external agencies) - Individual subscription
- **Admins** (company management) - Separate account type

**Total Lines of Code: 3,000+**

---

## 🎯 Key Accomplishment

**Simultaneous Multi-Function Accounts**: Users can have BOTH Talent + Hiring Manager functions active at the same time!

Example: Sarah is looking for a new job (Talent agent) while hiring for her current team (HM agent).

This is the **unique feature** that disrupts traditional job platforms.

---

## 📦 What Was Built

### 1. Database Models (900+ lines)

#### CompanyV2 Model (`company_v2.py`)
- Dual seat pool management (Hiring Manager + Talent seats)
- Seat allocation and tracking methods
- Subscription expiration tracking

```python
class Company(Base):
    hiring_manager_seats_allocated: int
    hiring_manager_seats_used: int
    talent_seats_allocated: int
    talent_seats_used: int

    def has_available_hiring_manager_seats() -> bool
    def allocate_hiring_manager_seat() -> bool
```

#### CompanyAdminAgent Model (`company_admin_agent.py`)
- Master AI for company knowledge
- Persists when hiring managers leave
- Tracks hiring metrics

```python
class CompanyAdminAgent(Base):
    company_rag_collection_id: str  # Company knowledge base
    total_hiring_managers: int
    active_hiring_managers: int
    total_hires: int
```

#### HiringManagerRole Model (`hiring_manager_role.py`)
- Links User → Company → Agents
- Tracks employment relationship
- Enables agent portability

```python
class HiringManagerRole(Base):
    user_id: int
    company_id: int
    hiring_manager_agent_id: int  # Personal (portable)
    company_admin_agent_id: int   # Master (stays)
    is_active: bool
```

#### Subscription Model (`subscription.py`)
- Payment and data retention
- "No payment = No data access" rule
- Grace period management

```python
class Subscription(Base):
    subscription_type: SubscriptionType
    expires_at: DateTime
    data_retention_expires_at: DateTime

    def has_data_access() -> bool  # Universal rule
```

#### CompanyAdminUser Model (`company_admin_user.py`)
- Separate admin account (not in AI network)
- Same email, different login key
- Permission management

---

### 2. Service Layer (1,300+ lines)

#### CompanyRAGManager (`company_rag.py` - 400 lines)
Manages company knowledge collections in ChromaDB.

**Key Methods:**
- `create_collection()`: Create company RAG
- `add_hiring_manager_knowledge()`: Populate from HM interviews
- `add_job_posting_knowledge()`: Add job data
- `query()`: Search company knowledge
- `remove_hiring_manager()`: Mark HM as historical when they leave

**Knowledge Types:**
- Hiring manager profiles
- Hiring preferences and style
- Team information
- Job postings
- Company culture

#### CompanyAgentFactory (`company_agent_factory.py` - 350 lines)
Creates and manages Company Admin Agents.

**Key Methods:**
- `create_for_company()`: Create Master AI for company
- `link_hiring_manager()`: Connect HM to company admin agent
- `deactivate_hiring_manager()`: Handle HM leaving (knowledge stays!)
- `add_job_posting()`: Add job data to company RAG
- `query_company_knowledge()`: Search company knowledge
- `get_company_knowledge_stats()`: Knowledge statistics

#### SubscriptionManager (`subscription_manager.py` - 400 lines)
Manages subscriptions, payments, and data retention.

**Key Methods:**
- `create_talent_free_trial()`: 12-month free trial
- `create_company_subscription()`: Seat-based billing
- `create_hiring_manager_subscription()`: Link to company seats
- `create_recruiter_subscription()`: Individual subscription
- `check_data_access()`: Enforce "No payment = No data" rule
- `upgrade_talent_to_paid()`: Convert from free to paid
- `renew_subscription()`: Renew expired subscription
- `cancel_subscription()`: Cancel with grace period

**Subscription Types:**
- `TALENT_FREE`: 12-month trial
- `TALENT_PAID`: Paid talent subscription
- `HIRING_MANAGER`: Company-based (uses company seat)
- `RECRUITER`: Individual subscription
- `COMPANY_SEATS`: Company seat pool subscription

---

### 3. API Endpoints (500+ lines)

#### Company Management API (`companies.py` - 500 lines)

**Endpoints:**

1. **POST /api/companies**
   - Create new company + admin agent
   - Allocate seat pools

2. **GET /api/companies/{id}**
   - Get company details
   - Show seat allocation status

3. **GET /api/companies/{id}/admin-agent**
   - Get Company Admin Agent details
   - View hiring metrics

4. **POST /api/companies/hiring-managers/link**
   - Link hiring manager to company
   - Add HM knowledge to company RAG

5. **POST /api/companies/hiring-managers/{role_id}/deactivate**
   - Deactivate HM (they left company)
   - Knowledge stays in company RAG

6. **POST /api/companies/subscriptions**
   - Create subscription (Talent, HM, Recruiter, Company)
   - Automatic seat allocation

7. **GET /api/companies/subscriptions/me**
   - Get current user's subscription status
   - Check data access

8. **POST /api/companies/subscriptions/{id}/cancel**
   - Cancel subscription
   - Grace period for data access

9. **POST /api/companies/{id}/knowledge/query**
   - Query company knowledge base
   - Available to HMs and admins

10. **GET /api/companies/{id}/knowledge/stats**
    - Get company knowledge statistics
    - View hiring metrics

---

### 4. Enhanced Registration System (`registration.py` - 600 lines)

**New Endpoints:**

#### 1. Talent Registration
**POST /api/registration/register/talent**

Creates base account:
- User account with email/password
- User profile
- Free 12-month trial subscription
- Email verification token

**Response:**
```json
{
  "user_id": 123,
  "email": "sarah@example.com",
  "subscription_type": "talent_free",
  "subscription_expires_at": "2026-11-08T...",
  "message": "Complete CV upload and interview to activate your AI agent"
}
```

#### 2. Add Hiring Manager Function
**POST /api/registration/add-function/hiring-manager**

Adds HM function to existing account:
- Creates or links to company
- Allocates company HM seat
- Creates HM subscription (linked to company)
- Creates HM role placeholder (completed after interview)

**Request:**
```json
{
  "company_id": 456,  // Optional: link to existing
  "company_name": "TechCorp",  // Required if creating new
  "company_description": "Leading tech company"
}
```

**Response:**
```json
{
  "hiring_manager_role_id": 789,
  "company_id": 456,
  "company_name": "TechCorp",
  "message": "Complete HM interview to activate your HM agent"
}
```

#### 3. Add Recruiter Function
**POST /api/registration/add-function/recruiter**

Adds Recruiter function:
- Creates individual Recruiter subscription
- Creates Recruiter agent placeholder
- For external recruitment agencies

**Request:**
```json
{
  "recruitment_company_name": "Elite Recruiters",
  "recruitment_company_description": "Tech recruitment specialists"
}
```

#### 4. User Functions Status
**GET /api/registration/me/functions**

Shows all active functions:
```json
{
  "user_id": 123,
  "email": "sarah@example.com",
  "has_talent_function": true,
  "has_hiring_manager_function": true,
  "has_recruiter_function": false,
  "talent_subscription_active": true,
  "hiring_manager_company": "TechCorp",
  "recruiter_company": null
}
```

---

## 🏗️ Architecture Patterns

### 1. Dual RAG System

**Personal HM Agent RAG:**
- Individual hiring style and preferences
- Portable when HM leaves company
- Owned by individual

**Company Admin Agent RAG:**
- All hiring managers' knowledge
- Job postings and company info
- Persists forever
- Owned by company

### 2. Agent Portability with Knowledge Retention

When hiring manager leaves company:
1. **HM Personal Agent**: Goes with them (portable)
2. **Company knowledge**: Stays in company RAG (retained)
3. **HM marked as historical**: Knowledge flagged but not deleted

### 3. Seat Licensing

**Separate Pools:**
- Hiring Manager seats (e.g., 10 seats at $49.99/month each)
- Talent seats (e.g., 20 seats at $9.99/month each)

**Flexible Allocation:**
- Company allocates seats as needed
- Talent seats can be for internal use OR sponsorship/donations

### 4. Subscription-Based Data Access

**Universal Rule: "No payment = No data access" (like iCloud)**

```python
def has_data_access() -> bool:
    if subscription.is_active():
        return True
    if subscription.data_retention_expires_at > now():
        return True  # Grace period
    return False  # Data locked
```

**Grace Period:**
- 30 days after subscription expires
- Data still accessible during grace period
- Must renew to avoid data loss

---

## 📊 Model Updates

### PersonalAIAgent Enhancements

**New Agent Types:**
```python
class AgentType(str, Enum):
    JOBSEEKER = "jobseeker"
    HIRING_MANAGER = "hiring_manager"  # NEW
    RECRUITER = "recruiter"  # NEW
    COMPANY = "company"  # Legacy
```

**New Fields:**
- `recruitment_company_name`: For recruiters
- `recruitment_company_description`: For recruiters

### User Model Enhancements

**New Fields:**
- `first_name`: First name
- `last_name`: Last name

(Maintains `full_name` for backward compatibility)

---

## 🔄 User Journey Examples

### Example 1: Sarah (Talent → Talent + HM)

**Day 1 - Register as Talent:**
```
POST /api/registration/register/talent
→ Creates account with 12-month free trial
→ Sarah completes CV upload + interview
→ Talent agent activated
```

**Day 30 - Add HM Function:**
```
POST /api/registration/add-function/hiring-manager
→ Links to TechCorp company
→ Allocates HM seat from company pool
→ Sarah completes HM interview
→ HM agent activated
```

**Result:** Sarah now has BOTH agents active!
- **Talent Agent**: Looking for better opportunities
- **HM Agent**: Hiring engineers for her team

### Example 2: Company (TechCorp) Onboarding

**Step 1 - First HM joins:**
```
POST /api/companies
→ Creates TechCorp company
→ Creates Company Admin Agent
→ Allocates 10 HM seats + 20 Talent seats
```

**Step 2 - Additional HMs join:**
```
POST /api/companies/hiring-managers/link
→ Links HM to existing TechCorp
→ Uses company seat pool
→ Adds HM knowledge to company RAG
```

**Step 3 - HM leaves company:**
```
POST /api/companies/hiring-managers/{role_id}/deactivate
→ HM agent goes with them (portable!)
→ Knowledge stays in company RAG (retained!)
→ Company seat freed up
```

---

## 🎯 Unique Features Implemented

### 1. Simultaneous Multi-Function Accounts
**First platform where users can be BOTH job seekers AND hiring managers at the same time!**

### 2. Agent Portability
**Hiring managers take their personal agents when they leave, but company keeps the knowledge.**

### 3. Dual RAG Knowledge System
**Personal knowledge (portable) + Company knowledge (persistent)**

### 4. AI-Native CV Revolution
**Replacing PDF/DOCX with structured, queryable, behavioral agent data.**

### 5. Universal Data Retention Rule
**"No payment = No data access" applies to ALL user types (like iCloud).**

---

## 📁 Files Created/Modified

### New Files (9 files):
1. `src/networking_ai/models/company_v2.py`
2. `src/networking_ai/models/company_admin_agent.py`
3. `src/networking_ai/models/hiring_manager_role.py`
4. `src/networking_ai/models/company_admin_user.py`
5. `src/networking_ai/models/subscription.py`
6. `src/networking_ai/services/company_rag.py`
7. `src/networking_ai/services/company_agent_factory.py`
8. `src/networking_ai/services/subscription_manager.py`
9. `src/networking_ai/api/companies.py`
10. `src/networking_ai/api/registration.py`

### Modified Files (6 files):
1. `src/networking_ai/models/__init__.py`
2. `src/networking_ai/models/personal_ai_agent.py`
3. `src/networking_ai/models/user.py`
4. `src/networking_ai/api/main.py`
5. `scripts/init_db_standalone.py`
6. `init_test_db.py`
7. `validate_phase1_db.py`

---

## 🧪 Database Schema

### New Tables (4 tables):
1. **company_admin_agents**: Master AI for companies
2. **hiring_manager_roles**: User → Company → Agent links
3. **company_admin_users**: Separate admin accounts
4. **subscriptions**: Payment and data retention

### Updated Tables (3 tables):
1. **companies**: Added seat allocation fields
2. **personal_ai_agents**: Added agent types and recruiter fields
3. **users**: Added first_name, last_name

---

## 📝 Next Steps (Phase 2 Week 3)

### Recommended Priorities:

1. **Job Posting as AI Agent**
   - Implement HM interview flow (similar to Talent interview)
   - Create job posting as Company AI Agent
   - Link job posting to hiring manager

2. **Agent Matching Logic**
   - Implement matching between Talent and HM agents
   - Query both Personal RAG and Company RAG
   - Present 3 matches per day

3. **Agent-to-Agent Conversations**
   - Implement conversation framework
   - Use both RAG systems for context
   - Track conversation outcomes

4. **Admin Dashboard**
   - Company admin UI for seat management
   - View hiring metrics
   - Manage subscriptions

5. **Payment Integration**
   - Stripe/payment gateway integration
   - Subscription renewal automation
   - Grace period notifications

---

## 🚀 Testing Recommendations

### Database Validation:
```bash
python validate_phase1_db.py
```

Should show:
- ✅ All Phase 1 tables
- ✅ All Phase 2 tables (company_admin_agents, hiring_manager_roles, etc.)

### API Testing:

1. **Register as Talent:**
```bash
POST /api/registration/register/talent
{
  "email": "test@example.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

2. **Add HM Function:**
```bash
POST /api/registration/add-function/hiring-manager
{
  "company_name": "Test Company",
  "company_description": "A test company"
}
```

3. **Check Functions:**
```bash
GET /api/registration/me/functions
```

---

## 📈 Metrics

- **Total Lines of Code**: 3,000+
- **Database Models**: 5 new models
- **Service Classes**: 3 new services
- **API Endpoints**: 14 new endpoints
- **Git Commits**: 3 major commits
- **Documentation**: This summary + inline comments

---

## 🎉 Summary

Phase 2 Week 2 successfully implements the **multi-user architecture** that enables:

✅ **Simultaneous multi-function accounts** (unique feature!)
✅ **Agent portability** with knowledge retention
✅ **Dual RAG system** (Personal + Company)
✅ **Seat-based licensing** with separate pools
✅ **Subscription-based data access** (universal rule)
✅ **Company knowledge persistence**
✅ **AI-native professional networking**

**This lays the foundation for the revolutionary "AI-native CV" platform that disrupts traditional job boards like LinkedIn, Indeed, and Adobe/Microsoft document formats!**

---

## 📞 Support

For questions or issues:
1. Check the inline code documentation
2. Review this summary document
3. Test with provided endpoints
4. Validate database schema

---

*Phase 2 Week 2 completed on 2025-11-08*
