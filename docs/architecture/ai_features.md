# AI Features Guide

## Overview

Networking AI integrates Anthropic's Claude for intelligent profile analysis, personalized introductions, and connection explanations. This guide covers all AI-powered features.

## Setup

### API Key Configuration

Set your Anthropic API key as an environment variable:

```bash
# Linux/macOS
export ANTHROPIC_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your_api_key_here"

# Or create a .env file
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

### Configuration

Customize AI behavior in `.env`:

```bash
ANTHROPIC_API_KEY=your_key
DEFAULT_MODEL=claude-3-5-sonnet-20241022
MAX_TOKENS=4096
TEMPERATURE=0.7
ENABLE_AI_ANALYSIS=true
```

## Features

### 1. Profile Analysis

Analyze profiles to extract insights:

```python
from networking_ai import AnthropicAgent

agent = AnthropicAgent()

profile = {
    "name": "Alice Johnson",
    "skills": ["Python", "Machine Learning", "Data Science"],
    "bio": "ML Engineer building recommendation systems",
    "goals": "Lead AI teams at a tech company"
}

analysis = agent.analyze_profile(profile)
print(analysis)
# {
#     "strengths": ["Machine Learning expertise", "Python proficiency", ...],
#     "interests": ["AI/ML applications", "Data-driven products", ...],
#     "goals": ["Technical leadership", "Team management", ...],
#     "value_proposition": "Experienced ML engineer with..."
# }
```

### 2. Connection Explanations

Generate explanations for why two profiles match:

```python
profile1 = {
    "name": "Alice",
    "skills": ["Python", "Machine Learning"],
    "interests": ["AI Research"]
}

profile2 = {
    "name": "Bob",
    "skills": ["Python", "Neural Networks"],
    "interests": ["Deep Learning"]
}

match_scores = {
    "overall_score": 0.87,
    "skill_score": 0.92,
    "weighted_score": 0.89
}

explanation = agent.explain_match(profile1, profile2, match_scores)
print(explanation)
# "Alice and Bob share strong technical alignment in Python and AI,
#  with complementary expertise in ML and neural networks..."
```

### 3. Personalized Introductions

Generate introduction messages:

```python
introduction = agent.generate_introduction(profile1, profile2, match_scores)
print(introduction)
# "Alice, I'd like to introduce you to Bob. You both work extensively
#  in Python and AI, and Bob's deep learning expertise could complement
#  your machine learning background perfectly."
```

### 4. Conversation Starters

Suggest topics for initial conversations:

```python
starters = agent.suggest_conversation_starters(profile1, profile2)
for starter in starters:
    print(f"- {starter}")
# - "What challenges have you faced implementing neural networks in production?"
# - "I'd love to hear about your approach to ML model optimization"
# - "Have you explored any interesting AI research papers recently?"
```

### 5. Profile Enrichment

Automatically enrich profiles with AI insights:

```python
from networking_ai import NetworkingAgent

agent = NetworkingAgent(name="EnrichBot")

basic_profile = {
    "user_id": "alice",
    "name": "Alice",
    "skills": ["Python", "ML"]
}

enriched = agent.enrich_profile(basic_profile)
print(enriched)
# {
#     ...original fields...,
#     "ai_insights": {
#         "strengths": [...],
#         "interests": [...],
#         "goals": [...],
#         "value_proposition": "..."
#     }
# }
```

## Integration with Recommendations

### Full-Featured Recommendations

```python
from networking_ai import ConnectionRecommender

recommender = ConnectionRecommender()

recommendations = recommender.recommend_connections(
    user,
    candidates,
    top_n=5,
    include_explanations=True,   # AI explanations
    include_introductions=True   # AI introductions
)

for rec in recommendations:
    print(f"\n{rec['name']} ({rec['match_strength']} match)")
    print(f"Score: {rec['match_scores']['weighted_score']:.2f}")
    print(f"\nWhy this match:")
    print(rec['explanation'])
    print(f"\nIntroduction:")
    print(rec['introduction'])
```

### Selective AI Usage

Control when to use AI features:

```python
# Without AI features (faster, no API key needed)
recommendations = recommender.recommend_connections(
    user,
    candidates,
    include_explanations=False,
    include_introductions=False
)

# With explanations only
recommendations = recommender.recommend_connections(
    user,
    candidates,
    include_explanations=True,
    include_introductions=False
)
```

## Best Practices

### 1. Error Handling

Always handle potential API errors:

```python
try:
    agent = AnthropicAgent()
    analysis = agent.analyze_profile(profile)
except ValueError as e:
    print(f"API key not configured: {e}")
except Exception as e:
    print(f"API error: {e}")
```

### 2. Rate Limiting

Respect API rate limits:

```python
import time

for profile in large_profile_list:
    enriched = agent.enrich_profile(profile)
    time.sleep(0.1)  # Small delay between requests
```

### 3. Cost Management

AI features consume API tokens:

- Use `include_explanations=False` for bulk operations
- Cache results when possible
- Set `ENABLE_AI_ANALYSIS=false` to disable globally

### 4. Batch Operations

For batch recommendations, disable AI features:

```python
# Efficient for large batches
batch_results = recommender.batch_recommend(
    users,
    candidates,
    top_n_per_user=5
)
# AI features are automatically disabled in batch mode
```

## Configuration Options

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional - Model Selection
DEFAULT_MODEL=claude-3-5-sonnet-20241022     # Default
# DEFAULT_MODEL=claude-3-opus-20240229       # More powerful
# DEFAULT_MODEL=claude-3-haiku-20240307      # Faster/cheaper

# Optional - Generation Parameters
MAX_TOKENS=4096              # Max response length
TEMPERATURE=0.7              # Creativity (0-1)

# Optional - Feature Flags
ENABLE_AI_ANALYSIS=true      # Enable/disable AI features
```

### Model Selection Guide

- **claude-3-5-sonnet-20241022**: Best balance (recommended)
- **claude-3-opus-20240229**: Highest quality, slower, more expensive
- **claude-3-haiku-20240307**: Fastest, cheaper, good quality

## Troubleshooting

### "API key not set" Error

```python
# Check if key is set
from networking_ai import config

if config.ANTHROPIC_API_KEY:
    print("✓ API key is configured")
else:
    print("✗ Set ANTHROPIC_API_KEY environment variable")
```

### AI Features Disabled

AI features auto-disable if:
- No API key is set
- `ENABLE_AI_ANALYSIS=false` in config
- API errors occur during initialization

```python
from networking_ai import NetworkingAgent

agent = NetworkingAgent(name="TestAgent")

if agent.ai_agent:
    print("✓ AI features enabled")
else:
    print("✗ AI features disabled")
```

### Rate Limit Errors

If you hit rate limits:
1. Add delays between requests
2. Use batch processing sparingly
3. Cache results
4. Consider upgrading your Anthropic plan

## Examples

See [examples/basic_usage.py](../examples/basic_usage.py) for complete examples using AI features.

## API Costs

Anthropic charges based on tokens (input + output):
- Typical profile analysis: ~500-1000 tokens
- Introduction generation: ~300-600 tokens
- Explanation: ~400-800 tokens

Monitor your usage in the Anthropic console.
