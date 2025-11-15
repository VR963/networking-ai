# Phase 2 Architecture Design
## Personal Agent Activation & Agent-to-Agent Conversations

**Status**: 🚧 In Design
**Date**: November 7, 2025
**Branch**: `claude/incomplete-description-011CUrqbA1f7a1dpLkRD64Xg`

---

## Overview

Phase 2 brings the AI Agent Marketplace to life. After Phase 1's onboarding interview, we now activate personal AI agents that represent users and conduct agent-to-agent negotiations for job matches.

**Core Concept**: Instead of users browsing job posts, their personal AI agent searches, evaluates, and negotiates with company agents autonomously. Users only see the best 3 matches per day after agents have already vetted them.

---

## Architecture Components

```
┌────────────────────────────────────────────────────────────────┐
│                         Phase 2: Activation                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Personal Agent Creation (from Interview)                   │
│     ├── Parse interview knowledge                              │
│     ├── Create PersonalAIAgent record                          │
│     ├── Build personal RAG collection                          │
│     └── Activate for matching                                  │
│                                                                 │
│  2. Personal RAG System                                        │
│     ├── ChromaDB collection per user                           │
│     ├── Interview knowledge as documents                       │
│     ├── User preferences and dealbreakers                      │
│     └── Conversation history for learning                      │
│                                                                 │
│  3. Agent Search Engine                                        │
│     ├── Company agents post job requirements                   │
│     ├── Personal agents search with hybrid approach            │
│     │   • Semantic search (ChromaDB)                           │
│     │   • Filter search (SQLAlchemy)                           │
│     │   • Ranking algorithm                                    │
│     └── Top N candidates returned                              │
│                                                                 │
│  4. Agent-to-Agent Conversations                               │
│     ├── Personal agent initiates with company agent            │
│     ├── Multi-turn dialogue (5-15 turns)                       │
│     ├── Information exchange (not interrogation)               │
│     ├── Mutual agreement detection                             │
│     └── Synopsis generation                                    │
│                                                                 │
│  5. Match Presentation                                         │
│     ├── Maximum 3 matches per day                              │
│     ├── User must respond to EACH match                        │
│     ├── Feedback collection                                    │
│     └── Learning loop back to Master AI                        │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 1. Personal Agent Creation

### Flow

```
Interview Complete
    ↓
Extract Knowledge
    ↓
Create PersonalAIAgent Record
    ↓
Build Personal RAG Collection
    ↓
Activate Agent (status = ACTIVE)
    ↓
Ready for Matching
```

### Implementation

**Service**: `PersonalAgentFactory`

```python
class PersonalAgentFactory:
    """Creates and activates personal AI agents."""

    def create_from_interview(
        self,
        session_id: int,
        db: Session
    ) -> PersonalAIAgent:
        """
        Create personal agent from completed interview.

        Steps:
        1. Load interview session
        2. Extract knowledge from conversation
        3. Generate user segment ID
        4. Create ChromaDB collection
        5. Populate personal RAG
        6. Create PersonalAIAgent record
        7. Mark agent as ACTIVE

        Returns:
            PersonalAIAgent instance
        """
        pass
```

**Personal RAG Structure**:
```python
{
  "collection_id": "user_{user_id}_personal_rag",
  "documents": [
    {
      "id": "cv_summary",
      "content": "8 years finance, trading systems, Python expert",
      "metadata": {"type": "profile", "source": "cv"}
    },
    {
      "id": "motivation_work_life_balance",
      "content": "Wants better work-life balance, current role 60+ hrs/week",
      "metadata": {"type": "motivation", "priority": "high"}
    },
    {
      "id": "dealbreaker_no_oncall",
      "content": "Will not accept on-call roles, needs predictable hours",
      "metadata": {"type": "dealbreaker", "hard": true}
    },
    {
      "id": "preference_company_stage",
      "content": "Prefers established companies (Series B+), not early startups",
      "metadata": {"type": "preference", "strength": 0.8}
    }
  ]
}
```

### Database Updates

**PersonalAIAgent** (already exists, update status):
```python
class AgentStatus(str, Enum):
    PENDING = "pending"          # Interview in progress
    READY = "ready"              # Interview complete, not yet activated
    ACTIVE = "active"            # Searching for matches
    PAUSED = "paused"            # User paused agent
    DISABLED = "disabled"        # User disabled agent

# Add to PersonalAIAgent model
status = Column(SQLEnum(AgentStatus), default=AgentStatus.PENDING)
activated_at = Column(DateTime)
last_search_at = Column(DateTime)
```

---

## 2. Personal RAG System

### Architecture

Each user gets their own ChromaDB collection:
- Collection ID: `user_{user_id}_personal_rag`
- Stored in ChromaDB alongside Master RAG
- Populated from interview knowledge
- Updated from conversation feedback

### Document Types

1. **Profile Documents** (from CV)
   - Work history
   - Skills and expertise
   - Education and certifications

2. **Motivation Documents** (from interview)
   - Career goals
   - What drives the user
   - Success criteria

3. **Preference Documents** (from interview)
   - Company stage (startup vs established)
   - Industry preferences
   - Work culture preferences
   - Compensation expectations

4. **Dealbreaker Documents** (from interview)
   - Hard no's (on-call, travel, etc.)
   - Must-haves (remote work, benefits, etc.)

5. **Learning Documents** (from feedback)
   - Past match feedback
   - What worked/didn't work
   - Pattern learning

### Implementation

**Service**: `PersonalRAGManager`

```python
class PersonalRAGManager:
    """Manages personal RAG collections per user."""

    def create_collection(self, user_id: int) -> str:
        """Create personal RAG collection for user."""
        collection_id = f"user_{user_id}_personal_rag"
        self.client.create_collection(collection_id)
        return collection_id

    def populate_from_interview(
        self,
        collection_id: str,
        knowledge: dict,
        cv_data: dict
    ):
        """Populate RAG from interview knowledge."""
        documents = []

        # CV summary
        documents.append({
            "id": "cv_summary",
            "content": self._generate_cv_summary(cv_data),
            "metadata": {"type": "profile", "source": "cv"}
        })

        # Motivations
        for motivation_key, motivation_data in knowledge.get("motivations", {}).items():
            documents.append({
                "id": f"motivation_{motivation_key}",
                "content": str(motivation_data),
                "metadata": {"type": "motivation", "priority": "high"}
            })

        # Preferences
        for pref_key, pref_data in knowledge.get("preferences", {}).items():
            documents.append({
                "id": f"preference_{pref_key}",
                "content": str(pref_data),
                "metadata": {"type": "preference"}
            })

        # Add all documents
        self.collection.add(documents=documents)

    def query(
        self,
        collection_id: str,
        query: str,
        filter: dict = None,
        n_results: int = 5
    ) -> List[dict]:
        """Query personal RAG."""
        return self.collection.query(
            query_texts=[query],
            where=filter,
            n_results=n_results
        )
```

---

## 3. Agent Search Engine

### Search Flow

```
Company Agent Posts Job
    ↓
Job Requirements → Master RAG (industry training)
    ↓
Personal Agents Search (nightly batch)
    ↓
Hybrid Search:
  1. Semantic Match (ChromaDB - skills, experience)
  2. Filter Match (SQL - location, salary, dealbreakers)
  3. Rank by Score
    ↓
Top N Candidates (e.g., top 50)
    ↓
Store as Potential Matches
```

### Search Algorithm

**Hybrid Approach**:

```python
def search_candidates(job_posting: JobPosting) -> List[Candidate]:
    """
    Hybrid search for candidates.

    Steps:
    1. Semantic search: Find users with relevant skills/experience
    2. Filter: Remove dealbreaker mismatches
    3. Rank: Score based on fit
    4. Return: Top N candidates
    """

    # Step 1: Semantic search
    semantic_results = chromadb.query(
        collection="all_user_profiles",
        query_text=job_posting.requirements,
        n_results=200  # Oversample
    )

    # Step 2: Filter dealbreakers
    filtered = []
    for result in semantic_results:
        user_id = result["user_id"]

        # Check dealbreakers
        if job_posting.requires_oncall and user_dealbreaker_no_oncall(user_id):
            continue
        if job_posting.salary_max < user_minimum_salary(user_id):
            continue
        if job_posting.location not in user_acceptable_locations(user_id):
            continue

        filtered.append(result)

    # Step 3: Rank
    ranked = rank_candidates(filtered, job_posting)

    # Step 4: Return top N
    return ranked[:50]
```

**Ranking Formula**:

```python
def calculate_match_score(user, job) -> float:
    """
    Calculate match score (0-1).

    Factors:
    - Skills match (40%)
    - Experience level match (20%)
    - Motivation alignment (15%)
    - Company stage preference (10%)
    - Compensation fit (10%)
    - Location preference (5%)
    """

    score = 0.0

    # Skills (40%)
    skills_overlap = len(set(user.skills) & set(job.required_skills))
    skills_score = skills_overlap / len(job.required_skills)
    score += skills_score * 0.4

    # Experience (20%)
    exp_diff = abs(user.years_experience - job.required_years)
    exp_score = max(0, 1 - (exp_diff / 5))  # Decay over 5 years
    score += exp_score * 0.2

    # Motivation (15%) - semantic similarity
    motivation_score = semantic_similarity(
        user.motivations,
        job.company_culture
    )
    score += motivation_score * 0.15

    # Company stage (10%)
    if job.company_stage in user.preferred_stages:
        score += 0.1

    # Compensation (10%)
    if job.salary_min <= user.expected_salary <= job.salary_max:
        score += 0.1
    elif job.salary_max >= user.minimum_salary:
        score += 0.05  # Acceptable but not ideal

    # Location (5%)
    if job.location in user.preferred_locations:
        score += 0.05

    return score
```

### Database Schema

**JobPosting** (new model):
```python
class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    company_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"))

    # Job details
    title = Column(String(255))
    description = Column(Text)
    requirements = Column(Text)

    # Structured requirements
    required_skills = Column(JSON)  # ["Python", "AWS", "Kubernetes"]
    required_years = Column(Integer)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    location = Column(String(255))
    remote_ok = Column(Boolean, default=False)
    requires_oncall = Column(Boolean, default=False)

    # Company context
    company_stage = Column(String(50))  # "startup", "series_b", "public"
    company_culture = Column(Text)

    # Status
    status = Column(String(50))  # "active", "paused", "filled"
    posted_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
```

**PotentialMatch** (new model):
```python
class PotentialMatch(Base):
    __tablename__ = "potential_matches"

    id = Column(Integer, primary_key=True)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"))
    candidate_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"))

    # Matching
    match_score = Column(Float)  # 0-1
    search_rank = Column(Integer)  # Position in search results

    # Status
    status = Column(String(50))  # "pending", "conversation_started", "presented", "accepted", "rejected"

    # Timestamps
    found_at = Column(DateTime, default=datetime.utcnow)
    conversation_started_at = Column(DateTime)
    presented_to_user_at = Column(DateTime)
```

---

## 4. Agent-to-Agent Conversations

### Conversation Flow

```
Personal Agent finds potential match
    ↓
Initiates conversation with Company Agent
    ↓
Multi-turn dialogue (5-15 turns):
  - Personal Agent: Asks about role, culture, expectations
  - Company Agent: Asks about skills, experience, availability
  - Both: Exchange information, evaluate fit
    ↓
Convergence Detection:
  - Mutual interest detected? → Continue
  - Dealbreaker found? → Stop
  - Enough information? → Summarize
    ↓
Agreement Reached or Not
    ↓
Synopsis Generated
    ↓
If Agreement → Present to User
If Not → Log and move on
```

### Conversation Types

**1. Information Exchange** (Turns 1-5)
- Personal Agent introduces candidate
- Company Agent shares role details
- Both ask clarifying questions

**2. Deep Dive** (Turns 6-10)
- Technical depth discussion
- Culture fit exploration
- Compensation alignment
- Availability and timeline

**3. Convergence** (Turns 11-15)
- Summarize mutual understanding
- Identify any concerns
- Determine if match worthy of human review

### Implementation

**Service**: `AgentNegotiator`

```python
class AgentNegotiator:
    """Manages agent-to-agent negotiations."""

    def start_conversation(
        self,
        personal_agent: PersonalAIAgent,
        company_agent: PersonalAIAgent,
        job_posting: JobPosting
    ) -> AgentConversation:
        """
        Start agent-to-agent conversation.

        Returns:
            AgentConversation instance
        """

        # Create conversation record
        conversation = AgentConversation(
            agent1_id=personal_agent.id,
            agent2_id=company_agent.id,
            conversation_type=ConversationType.AGENT_TO_AGENT,
            status=ConversationStatus.ACTIVE
        )
        db.add(conversation)
        db.commit()

        # Personal agent opens
        opening = self._generate_opening_message(
            personal_agent,
            job_posting
        )

        conversation.add_message(
            role="personal_agent",
            content=opening
        )

        return conversation

    def continue_conversation(
        self,
        conversation: AgentConversation,
        max_turns: int = 15
    ) -> dict:
        """
        Continue conversation until convergence or max turns.

        Returns:
            {
                "status": "agreement" | "no_match" | "needs_review",
                "synopsis": "...",
                "mutual_interest": bool,
                "concerns": [...]
            }
        """

        while conversation.turn_count < max_turns:
            # Determine whose turn
            next_agent = self._determine_next_speaker(conversation)

            # Generate response
            response = self._generate_agent_response(
                conversation,
                next_agent
            )

            # Add to conversation
            conversation.add_message(
                role=next_agent.role,
                content=response
            )

            # Check convergence
            convergence = self._check_convergence(conversation)
            if convergence["reached"]:
                break

        # Generate synopsis
        synopsis = self._generate_synopsis(conversation)

        return {
            "status": convergence["status"],
            "synopsis": synopsis,
            "mutual_interest": convergence["mutual_interest"],
            "concerns": convergence["concerns"]
        }
```

**Convergence Detection**:
```python
def _check_convergence(self, conversation: AgentConversation) -> dict:
    """
    Detect if conversation has reached conclusion.

    Signals:
    - Dealbreaker mentioned (stop immediately)
    - Mutual interest expressed (present to user)
    - Information saturation (enough data gathered)
    - Repetitive questions (not progressing)
    """

    # Analyze last 3 messages
    recent_messages = conversation.messages[-3:]

    # Check for dealbreakers
    for msg in recent_messages:
        if "deal breaker" in msg["content"].lower():
            return {
                "reached": True,
                "status": "no_match",
                "reason": "dealbreaker_found"
            }

    # Check for mutual interest
    personal_interested = False
    company_interested = False

    for msg in recent_messages:
        if msg["role"] == "personal_agent" and "interested" in msg["content"].lower():
            personal_interested = True
        if msg["role"] == "company_agent" and "great fit" in msg["content"].lower():
            company_interested = True

    if personal_interested and company_interested:
        return {
            "reached": True,
            "status": "agreement",
            "mutual_interest": True
        }

    # Check information saturation
    if conversation.turn_count >= 10:
        # Use AI to analyze if enough info gathered
        analysis = self._analyze_information_completeness(conversation)
        if analysis["complete"]:
            return {
                "reached": True,
                "status": "needs_review" if analysis["promising"] else "no_match"
            }

    return {"reached": False}
```

---

## 5. Match Presentation

### Rules

1. **Maximum 3 matches per day**
2. **User must respond to EACH match before seeing next**
3. **Feedback required**: Accept/Reject + Reason
4. **Learning loop**: Feedback → UserKnowledge → NetworkKnowledge → Master AI

### Flow

```
Agent-to-Agent Agreement Reached
    ↓
Add to User's Match Queue
    ↓
Check: Has user seen 3 matches today?
  Yes → Wait until tomorrow
  No → Present match
    ↓
User Reviews Match:
  - Views conversation synopsis
  - Sees job details
  - Reads agent's assessment
    ↓
User Decides:
  Accept → Create formal Match → Notify company
  Reject → Collect reason → Update learning
  Skip → Move to next match
    ↓
Feedback Loop:
  - Update UserKnowledge
  - Extract patterns → NetworkKnowledge
  - Master AI learns for future
```

### Implementation

**Service**: `MatchPresenter`

```python
class MatchPresenter:
    """Presents matches to users."""

    def present_daily_matches(
        self,
        user_id: int,
        db: Session
    ) -> List[PresentedMatch]:
        """
        Present up to 3 matches to user.

        Rules:
        - Max 3 per day
        - Must respond to each before next
        - Ordered by match score
        """

        # Check today's quota
        today_count = self._get_todays_presented_count(user_id)
        if today_count >= 3:
            return []  # Already at limit

        # Get pending matches
        pending = self._get_pending_matches(user_id)

        # Present up to remaining quota
        remaining = 3 - today_count
        to_present = pending[:remaining]

        for match in to_present:
            match.status = "presented"
            match.presented_to_user_at = datetime.utcnow()

        db.commit()

        return to_present

    def collect_feedback(
        self,
        match_id: int,
        decision: str,  # "accept", "reject", "skip"
        reason: str,
        db: Session
    ):
        """
        Collect user feedback on match.

        Learning:
        - Accept → What made this good?
        - Reject → What was the issue?
        - Skip → Why not interested?
        """

        match = db.query(PotentialMatch).get(match_id)

        # Update match
        match.status = f"user_{decision}"
        match.user_feedback = reason
        match.responded_at = datetime.utcnow()

        # Extract learning
        if decision == "accept":
            self._learn_from_accept(match, reason, db)
        elif decision == "reject":
            self._learn_from_reject(match, reason, db)

        db.commit()
```

---

## API Endpoints (Phase 2)

### Personal Agent Activation

```python
POST /api/agents/activate/{session_id}
```
Activate personal agent from completed interview.

Response:
```json
{
  "agent_id": 123,
  "status": "active",
  "collection_id": "user_45_personal_rag",
  "activated_at": "2025-11-07T12:00:00Z"
}
```

### Agent Control

```python
GET /api/agents/me
```
Get user's personal agent status.

```python
POST /api/agents/me/pause
POST /api/agents/me/resume
```
Pause/resume agent searching.

### Job Search (for companies)

```python
POST /api/jobs
```
Company posts job (creates company agent).

Request:
```json
{
  "title": "Senior Python Engineer",
  "description": "...",
  "required_skills": ["Python", "AWS", "Kubernetes"],
  "salary_min": 150000,
  "salary_max": 200000,
  "location": "San Francisco",
  "remote_ok": true
}
```

### Matches

```python
GET /api/matches/daily
```
Get today's matches (up to 3).

```python
POST /api/matches/{match_id}/respond
```
Respond to match.

Request:
```json
{
  "decision": "accept",  // or "reject", "skip"
  "reason": "Great culture fit and exciting role"
}
```

### Agent Conversations (View Only)

```python
GET /api/conversations/{conversation_id}
```
View agent-to-agent conversation transcript.

---

## Implementation Order

### Week 1: Personal Agent Foundation
1. PersonalAgentFactory service
2. PersonalRAGManager service
3. Agent activation endpoint
4. Database migrations

### Week 2: Search Engine
1. JobPosting model and API
2. Hybrid search implementation
3. Ranking algorithm
4. PotentialMatch tracking

### Week 3: Agent Conversations
1. AgentNegotiator service
2. Conversation management
3. Convergence detection
4. Synopsis generation

### Week 4: Match Presentation
1. MatchPresenter service
2. Daily quota system
3. Feedback collection
4. Learning loop

### Week 5: Testing & Integration
1. Unit tests
2. Integration tests
3. E2E flow tests
4. Performance optimization

---

## Success Metrics

### Technical Metrics
- Personal agent activation: <5 seconds
- Search query: <2 seconds for 1000 users
- Agent conversation: 5-15 turns average
- Match presentation: 3 per day per user

### Business Metrics
- User satisfaction with matches: >70%
- Accept rate on presented matches: >10%
- Time to first match: <24 hours
- False positive rate: <30%

### Cost Metrics
- Agent conversation: ~$0.30 per conversation
- Search query: $0.001 per query
- Daily cost per user: ~$0.50-$1.00

---

## Next Steps

1. ✅ Review Phase 2 architecture
2. Start implementation (Week 1)
3. Create migrations for new models
4. Build PersonalAgentFactory
5. Build PersonalRAGManager

---

*Phase 2 Architecture v1.0*
*Ready for implementation*
