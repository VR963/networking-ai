## Multi-Agent System Architecture

# Multi-Agent System Architecture

## Overview

Networking AI implements a sophisticated multi-agent architecture that combines LangChain agents, dual RAG systems, and privacy-first knowledge management.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                              │
│           (Coordinates all sub-agents and operations)                │
└────────────┬────────────────────────────────────────────────────────┘
             │
      ┌──────┴──────┐
      │  DELEGATES  │
      └──────┬──────┘
             │
   ┌─────────┼─────────────────────────────────────────────┐
   │         │                                              │
┌──▼──────┐  │  ┌────────────┐  ┌────────────┐  ┌─────────▼────┐
│Research │  │  │  Matching  │  │  Security  │  │   Knowledge   │
│ Agent   │  │  │   Agent    │  │   Agent    │  │     Agent     │
└────┬────┘  │  └─────┬──────┘  └─────┬──────┘  └────────┬──────┘
     │       │        │               │                   │
     │    ┌──▼──────┐ │               │                   │
     │    │  Note   │ │               │                   │
     │    │  Taker  │ │               │                   │
     │    │  Agent  │ │               │                   │
     │    └─────────┘ │               │                   │
     │                │               │                   │
     └────────────────┴───────────────┴───────────────────┘
                      │
          ┌───────────┴───────────┐
          │   SHARED RESOURCES    │
          └───────────┬───────────┘
                      │
        ┌─────────────┼─────────────────────┐
        │             │                     │
┌───────▼───────┐  ┌──▼─────────┐   ┌──────▼──────┐
│   DUAL RAG    │  │  SEMANTIC  │   │  LEARNING   │
│    SYSTEM     │  │   MATCHER  │   │   SYSTEM    │
└───────┬───────┘  └────────────┘   └─────────────┘
        │
   ┌────┴────┐
   │         │
┌──▼──────┐  └──▼────────────┐
│ PUBLIC  │     │   PRIVATE  │
│KNOWLEDGE│     │USER VAULT  │
│  BASE   │     │(Encrypted) │
└─────────┘     └────────────┘
```

## Core Components

### 1. Orchestrator Agent

**Role**: Main coordinator that receives user requests and delegates to appropriate sub-agents.

**Capabilities**:
- Request analysis and routing
- Multi-agent coordination
- Response synthesis
- Interaction history tracking

**Implementation**: `multi_agent_system.py::OrchestratorAgent`

### 2. Sub-Agents

#### Research Agent
- **Purpose**: Information gathering and trend analysis
- **Tools**:
  - `query_public_knowledge`: Search the public knowledge base
  - `get_knowledge_statistics`: Retrieve system statistics
- **Use Cases**: Skill trends, industry insights, general queries

#### Matching Agent
- **Purpose**: Profile similarity and matching analysis
- **Tools**:
  - `calculate_similarity`: Compare two profiles semantically
  - `find_skill_matches`: Calculate skill similarity scores
- **Use Cases**: Connection recommendations, profile comparisons

#### Security Agent
- **Purpose**: Privacy protection and PII detection
- **Tools**:
  - `check_pii`: Detect personally identifiable information
  - `anonymize_text`: Remove/redact PII from text
- **Use Cases**: Data validation, privacy compliance, security checks

#### Knowledge Agent
- **Purpose**: Knowledge management and learning
- **Tools**:
  - `learn_from_conversation`: Process and store interactions
  - `get_learning_stats`: Retrieve learning statistics
- **Use Cases**: Conversation logging, pattern extraction, knowledge updates

#### Note Taker Agent
- **Purpose**: Documentation and insight recording
- **Tools**:
  - `take_note`: Record observations
  - `get_notes`: Retrieve all notes
- **Use Cases**: Interaction logging, audit trails, debugging

### 3. Dual RAG System

#### Public Knowledge Base
**Purpose**: Store anonymized, shareable insights

**Features**:
- No password protection
- Automatic PII removal
- Semantic deduplication (95% threshold)
- Community-wide access
- Industry patterns and trends

**Storage**: ChromaDB with public collection

**Use Cases**:
- General skill information
- Industry trends
- Anonymized best practices
- Common patterns

#### Private User Vault
**Purpose**: Store encrypted personal data

**Features**:
- Password-protected access
- End-to-end encryption
- User-specific isolation
- PII-safe storage
- Last-accessed tracking

**Storage**: ChromaDB with encrypted private collection

**Use Cases**:
- Personal goals and preferences
- Confidential career information
- Private conversation history
- Sensitive user data

### 4. Knowledge Learning System

**Purpose**: Learn from interactions while maintaining privacy

**Components**:

1. **Conversation Deduplicator**
   - Semantic similarity detection (95% threshold)
   - Prevents storing repetitive content
   - Embedding-based comparison

2. **Quality Filter**
   - Scores conversations (0-1 scale)
   - Minimum threshold: 0.7
   - Factors: length, informativeness, specificity, relevance

3. **PII Detector**
   - Pattern-based detection
   - Identifies: emails, phones, addresses, etc.
   - Automatic anonymization

**Workflow**:
```
User Interaction
    ↓
Quality Check → Low quality? → Skip
    ↓
Deduplication → Duplicate? → Skip
    ↓
PII Detection
    ↓
┌───────────┴──────────┐
│                      │
Has PII?            No PII?
↓                      ↓
Authenticated?      Anonymize
↓                      ↓
Private Vault       Public KB
```

## Data Flow

### 1. User Request Processing

```
1. User submits request
2. Orchestrator analyzes request type
3. Orchestrator creates execution plan
4. Security Agent checks for PII (if user data present)
5. Relevant agents execute in parallel
6. Orchestrator synthesizes responses
7. Note Taker logs interaction
8. Final response returned
```

### 2. Knowledge Storage

```
1. Interaction occurs (Q&A)
2. Quality filter evaluates content
3. Deduplicator checks for similar content
4. PII detector scans for sensitive data
5a. If PII + authenticated → Private Vault (encrypted)
5b. If no PII → Public KB (anonymized)
6. Success/failure logged
```

### 3. Retrieval

**Public Knowledge**:
```
Query → Embedding Generation → Semantic Search → Results
```

**Private Data**:
```
Query + Password → Authentication → Embedding Generation →
User-filtered Search → Decryption → Results
```

## Privacy Architecture

### Data Separation

1. **Public Knowledge Base**
   - ✓ Anonymized content only
   - ✓ No PII
   - ✓ Community-accessible
   - ✓ Semantic deduplication
   - ✗ No personal information

2. **Private User Vault**
   - ✓ Encrypted at rest
   - ✓ Password-protected
   - ✓ User-isolated
   - ✓ PII-safe
   - ✗ Not shared between users

### Encryption

- **Algorithm**: Fernet (symmetric encryption)
- **Key Management**: Environment variable or generated
- **Password Hashing**: bcrypt with salt
- **Data in Transit**: Encrypted embeddings for search
- **Data at Rest**: Encrypted content storage

### Access Control

- **Public KB**: No authentication required
- **Private Vault**: Password required for each access
- **Cross-user**: Zero data sharing
- **Account Lifecycle**: 365-day inactivity → sleep mode

## Account Lifecycle

### States

1. **Active**: Regular usage (last_accessed < 365 days)
2. **Sleeping**: Inactive (365+ days), data preserved
3. **Deleted**: Manual deletion or 730+ days inactive

### Implementation

```python
def check_account_status(user_id):
    last_access = get_last_access(user_id)

    if days_since(last_access) > ACCOUNT_DELETE_DAYS:
        return "pending_deletion"
    elif days_since(last_access) > ACCOUNT_SLEEP_DAYS:
        return "sleeping"
    else:
        return "active"
```

## Configuration

### Environment Variables

```bash
# RAG System
CHROMADB_PATH=./data/chromadb
PUBLIC_KNOWLEDGE_COLLECTION=public_knowledge
PRIVATE_VAULT_COLLECTION=private_vault

# Security
ENCRYPTION_KEY=<fernet_key>
MASTER_SALT=<random_salt>

# Knowledge Learning
ENABLE_KNOWLEDGE_LEARNING=true
DEDUPLICATION_THRESHOLD=0.95
MIN_INTERACTION_QUALITY_SCORE=0.7

# Account Lifecycle
ACCOUNT_SLEEP_DAYS=365
ACCOUNT_DELETE_DAYS=730

# Multi-Agent
ENABLE_MULTI_AGENT=true
MAX_AGENT_ITERATIONS=10
AGENT_VERBOSE=false
```

## Performance Considerations

### Optimization Strategies

1. **Embedding Caching**: Cache computed embeddings
2. **Batch Processing**: Process multiple requests together
3. **Lazy Loading**: Load agents only when needed
4. **Index Optimization**: ChromaDB automatic indexing
5. **Connection Pooling**: Reuse database connections

### Scalability

- **Horizontal**: Multiple ChromaDB instances
- **Vertical**: Larger embedding models
- **Caching**: Redis for hot data
- **Distribution**: Separate agent services

## Security Best Practices

1. ✓ Never log passwords or encryption keys
2. ✓ Rotate encryption keys periodically
3. ✓ Validate all user inputs
4. ✓ Sanitize PII before public storage
5. ✓ Audit access logs regularly
6. ✓ Use HTTPS in production
7. ✓ Implement rate limiting
8. ✓ Regular security audits

## Future Enhancements

1. **Multi-modal support**: Images, PDFs, audio
2. **Federated learning**: Cross-organization insights
3. **Real-time collaboration**: Live agent interactions
4. **Advanced NLP**: Named entity recognition
5. **Compliance**: GDPR, CCPA automation
6. **Analytics**: Usage dashboards
7. **API Gateway**: REST/GraphQL endpoints

## Troubleshooting

### Common Issues

**Problem**: RAG system not finding results
- **Solution**: Check embedding model, verify data was added

**Problem**: Authentication failures
- **Solution**: Verify password, check user_id

**Problem**: PII not detected
- **Solution**: Update PII patterns, enhance detection rules

**Problem**: Agent coordination errors
- **Solution**: Check ANTHROPIC_API_KEY, verify agent initialization

## References

- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Sentence Transformers](https://www.sbert.net/)
