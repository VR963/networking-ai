# Semantic Matching Guide

## Overview

The semantic matching module provides intelligent profile matching using sentence transformers and cosine similarity. Unlike traditional keyword matching, semantic matching understands the meaning and context of skills, interests, and profile descriptions.

## Core Concepts

### Sentence Embeddings

Sentence transformers convert text into high-dimensional vectors (embeddings) that capture semantic meaning. Similar texts produce similar embeddings.

```python
from networking_ai import SemanticMatcher

matcher = SemanticMatcher()

# Generate embeddings
embedding1 = matcher.generate_embedding("Python programming")
embedding2 = matcher.generate_embedding("Python development")

# Calculate similarity
similarity = matcher.calculate_similarity(embedding1, embedding2)
print(f"Similarity: {similarity:.2f}")  # High score (>0.8)
```

### Profile Text Generation

Profiles are converted to text representations that combine multiple fields:

```python
profile = {
    "name": "Alice Johnson",
    "skills": ["Python", "Machine Learning"],
    "interests": ["AI Research"],
    "bio": "ML Engineer passionate about AI",
    "goals": "Build innovative AI products"
}

text = matcher.generate_profile_text(profile)
# Result: "Name: Alice Johnson | Skills: Python, Machine Learning | ..."
```

## Matching Profiles

### Basic Profile Matching

```python
from networking_ai import SemanticMatcher

matcher = SemanticMatcher()

profile1 = {
    "user_id": "alice",
    "name": "Alice",
    "skills": ["Python", "Machine Learning"]
}

profile2 = {
    "user_id": "bob",
    "name": "Bob",
    "skills": ["Python", "AI"]
}

scores = matcher.match_profiles(profile1, profile2)
print(scores)
# {
#     "overall_score": 0.87,
#     "skill_score": 0.92,
#     "weighted_score": 0.89
# }
```

### Score Components

- **overall_score**: Semantic similarity of complete profiles (0-1)
- **skill_score**: Specific similarity of skills (0-1)
- **weighted_score**: Combined score (60% overall + 40% skills)

### Finding Best Matches

```python
target = {"user_id": "alice", "skills": ["Python", "AI"]}

candidates = [
    {"user_id": "bob", "skills": ["Python", "Data Science"]},
    {"user_id": "charlie", "skills": ["JavaScript", "React"]},
    {"user_id": "david", "skills": ["Python", "Machine Learning"]},
]

# Get top 2 matches with minimum score of 0.6
matches = matcher.find_best_matches(
    target,
    candidates,
    top_n=2,
    min_score=0.6
)

for profile, scores in matches:
    print(f"{profile['user_id']}: {scores['weighted_score']:.2f}")
```

## Skill Similarity

Calculate similarity between skill sets:

```python
skills1 = ["Python", "Machine Learning", "Data Science"]
skills2 = ["Python", "AI", "Deep Learning"]

skill_similarity = matcher.calculate_skill_similarity(skills1, skills2)
print(f"Skill similarity: {skill_similarity:.2f}")
```

### How It Works

1. Generate embeddings for each skill in both lists
2. For each skill in list 1, find the most similar skill in list 2
3. Return the average of maximum similarities

## Configuration

### Custom Models

Use different sentence transformer models:

```python
# Faster but less accurate
matcher = SemanticMatcher(model_name="all-MiniLM-L6-v2")

# More accurate but slower
matcher = SemanticMatcher(model_name="all-mpnet-base-v2")

# Multilingual support
matcher = SemanticMatcher(model_name="paraphrase-multilingual-MiniLM-L12-v2")
```

### Caching

Embeddings are automatically cached for performance:

```python
# Embeddings are cached by default
embedding = matcher.generate_embedding("Python")  # Computed
embedding = matcher.generate_embedding("Python")  # Retrieved from cache

# Clear cache if needed
matcher.clear_cache()

# Disable caching for specific call
embedding = matcher.generate_embedding("Python", use_cache=False)
```

## Performance Tips

1. **Batch Processing**: Generate embeddings for all profiles upfront
2. **Caching**: Enable caching for repeated queries
3. **Model Selection**: Choose appropriate model for your use case
4. **Minimum Threshold**: Set reasonable `min_score` to filter low matches

## Threshold Guidelines

Recommended similarity thresholds:

- **0.9+**: Excellent match (almost identical profiles)
- **0.8-0.9**: Strong match (very similar)
- **0.7-0.8**: Good match (notable similarities)
- **0.6-0.7**: Moderate match (some commonalities)
- **<0.6**: Weak match (different profiles)

## Advanced Usage

### Custom Weighting

Modify the weighting in your application:

```python
scores = matcher.match_profiles(profile1, profile2)

# Custom weighting: 70% skills, 30% overall
custom_score = (0.3 * scores['overall_score']) + (0.7 * scores['skill_score'])
```

### Multi-Field Matching

Match specific profile aspects:

```python
# Match only interests
interests1 = ["AI Research", "Deep Learning"]
interests2 = ["Machine Learning", "Neural Networks"]

interest_similarity = matcher.calculate_skill_similarity(interests1, interests2)
```

## Troubleshooting

### Low Similarity Scores

- Check if profiles have sufficient text content
- Verify skills/interests are descriptive (not just acronyms)
- Consider using a different sentence transformer model

### Slow Performance

- Enable caching
- Use a smaller/faster model
- Pre-compute embeddings for static profiles
- Implement batch processing

### Memory Issues

- Clear cache periodically: `matcher.clear_cache()`
- Use a lighter model
- Process profiles in smaller batches
