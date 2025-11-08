# Mobile API Performance Testing Guide

**Version**: 1.0.0
**Last Updated**: 2025-11-08
**Target API**: Mobile API v1

---

## Overview

This guide provides comprehensive instructions for performance testing the Networking AI Mobile API, including benchmark targets, testing procedures, and optimization strategies.

## Performance Targets

### Response Time Targets

| Endpoint Type | Target (p50) | Target (p95) | Target (p99) |
|---------------|--------------|--------------|--------------|
| Authentication | <200ms | <500ms | <1000ms |
| Profile Retrieval | <150ms | <300ms | <600ms |
| Job Search (20 results) | <400ms | <800ms | <1500ms |
| Job Details | <200ms | <400ms | <800ms |
| Application Submission | <500ms | <1000ms | <2000ms |
| Notification List | <250ms | <500ms | <1000ms |
| Message Retrieval | <300ms | <600ms | <1200ms |

### Payload Size Targets

| Endpoint | Target Size | Maximum Size |
|----------|-------------|--------------|
| Job List (20 items) | <40KB | <50KB |
| Profile | <8KB | <10KB |
| Notification List (20) | <25KB | <30KB |
| Message Conversation | <30KB | <40KB |
| Job Details | <15KB | <20KB |

### Throughput Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Requests/second (single server) | >500 | >300 |
| Concurrent users | >1000 | >500 |
| Database connections | <50 | <100 |
| Average CPU usage | <60% | <80% |
| Average memory usage | <2GB | <4GB |

---

## Running Performance Tests

### Prerequisites

```bash
# Install testing dependencies
pip install pytest pytest-benchmark pytest-asyncio locust

# Create large test dataset
python scripts/seed_performance_data.py
```

### Run Performance Test Suite

```bash
# Run all performance benchmarks
pytest tests/test_mobile_performance.py -v --benchmark-only

# Run with output
pytest tests/test_mobile_performance.py -v --benchmark-only --benchmark-json=results.json

# Run specific benchmark
pytest tests/test_mobile_performance.py::test_job_search_response_time -v
```

### Generate Performance Report

```bash
# Generate HTML report
python scripts/generate_performance_report.py results.json > docs/performance_results.html
```

---

## Test Scenarios

### 1. Response Time Benchmarks

**Test**: Measure endpoint response times under normal load

**Procedure**:
1. Warm up: 10 requests to prime cache
2. Measure: 100 requests per endpoint
3. Calculate: p50, p95, p99 percentiles
4. Compare: Against targets

**Code Example**:
```python
import time
import statistics

def benchmark_endpoint(endpoint_func, iterations=100):
    """Benchmark an endpoint's response time."""
    times = []

    # Warm up
    for _ in range(10):
        endpoint_func()

    # Measure
    for _ in range(iterations):
        start = time.time()
        endpoint_func()
        duration = time.time() - start
        times.append(duration)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": sorted(times)[int(0.95 * len(times))],
        "p99": sorted(times)[int(0.99 * len(times))],
        "min": min(times),
        "max": max(times)
    }
```

### 2. Payload Size Tests

**Test**: Verify response payload sizes meet mobile optimization targets

**Procedure**:
1. Make API request
2. Measure response body size in bytes
3. Calculate size in KB
4. Compare against targets
5. Identify large fields if over target

**Code Example**:
```python
import json

def measure_payload_size(response):
    """Measure API response payload size."""
    body = json.dumps(response.json())
    size_bytes = len(body.encode('utf-8'))
    size_kb = size_bytes / 1024

    # Analyze large fields
    large_fields = {}
    for key, value in response.json().items():
        field_size = len(json.dumps(value).encode('utf-8')) / 1024
        if field_size > 5:  # Fields >5KB
            large_fields[key] = f"{field_size:.2f}KB"

    return {
        "size_bytes": size_bytes,
        "size_kb": round(size_kb, 2),
        "large_fields": large_fields
    }
```

### 3. Concurrent User Testing

**Test**: Measure performance under concurrent load

**Tool**: Use Locust for load testing

**locustfile.py**:
```python
from locust import HttpUser, task, between

class MobileAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login and get token."""
        response = self.client.post("/api/v1/mobile/auth/login", json={
            "email": "test@example.com",
            "password": "password123",
            "device": {
                "platform": "ios",
                "device_id": "test_device"
            }
        })
        self.token = response.json()["data"]["tokens"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def search_jobs(self):
        """Search jobs (most common action)."""
        self.client.get(
            "/api/v1/mobile/jobs",
            headers=self.headers,
            params={"limit": 20}
        )

    @task(2)
    def get_profile(self):
        """Get profile."""
        self.client.get(
            "/api/v1/mobile/profile",
            headers=self.headers
        )

    @task(1)
    def get_notifications(self):
        """Get notifications."""
        self.client.get(
            "/api/v1/mobile/notifications",
            headers=self.headers
        )
```

**Run Test**:
```bash
# Test with 100 concurrent users, spawn rate 10/sec
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m
```

### 4. Database Query Performance

**Test**: Identify slow queries and N+1 query problems

**Procedure**:
1. Enable query logging
2. Run endpoint tests
3. Analyze query counts and durations
4. Identify optimization opportunities

**SQL Analysis**:
```sql
-- Find slow queries (PostgreSQL)
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE mean_time > 100  -- Queries taking >100ms on average
ORDER BY total_time DESC
LIMIT 20;

-- Check for missing indexes
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / seq_scan as avg_seq_read
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;
```

### 5. Pagination Performance

**Test**: Verify pagination doesn't degrade for deep pages

**Procedure**:
1. Test first page response time
2. Test page 5, 10, 20 response times
3. Verify consistent performance
4. Check cursor encoding/decoding overhead

**Code Example**:
```python
def test_pagination_consistency():
    """Test pagination performance across pages."""
    results = {}
    cursor = None

    for page_num in [1, 5, 10, 20]:
        # Navigate to specific page
        for _ in range(page_num):
            start = time.time()
            response = api_client.get(
                "/api/v1/mobile/jobs",
                params={"cursor": cursor, "limit": 20}
            )
            duration = time.time() - start

            if page_num in [1, 5, 10, 20]:
                results[f"page_{page_num}"] = duration

            cursor = response.json()["data"]["meta"]["cursor"]

    # Verify consistency (no page should be 2x slower than first)
    first_page_time = results["page_1"]
    for page, time in results.items():
        assert time < first_page_time * 2, f"{page} too slow: {time}s"

    return results
```

---

## Performance Optimization Strategies

### 1. Database Optimization

#### Add Indexes
```sql
-- Jobs table indexes
CREATE INDEX idx_jobs_status ON jobs(status) WHERE status = 'OPEN';
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_company_id ON jobs(company_id);

-- Applications table indexes
CREATE INDEX idx_applications_user_job ON applications(user_id, job_id);
CREATE INDEX idx_applications_user_status ON applications(user_id, status);

-- Notifications table indexes
CREATE INDEX idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- SavedJobs table indexes
CREATE INDEX idx_saved_jobs_user_job ON saved_jobs(user_id, job_id);
```

#### Use Eager Loading
```python
# Bad: N+1 query problem
jobs = session.query(Job).limit(20).all()
for job in jobs:
    company = job.company  # Separate query for each job!

# Good: Eager load relationships
from sqlalchemy.orm import joinedload

jobs = session.query(Job)\
    .options(joinedload(Job.company))\
    .limit(20)\
    .all()
```

#### Use SELECT Specific Fields
```python
# Bad: SELECT *
jobs = session.query(Job).all()

# Good: Select only needed fields
jobs = session.query(
    Job.id,
    Job.title,
    Job.location,
    Job.min_salary,
    Job.max_salary
).all()
```

### 2. Response Optimization

#### Compact Response Schemas
```python
# Use compact schemas for list views
class JobCompact(BaseModel):
    id: int
    title: str
    company: CompanyCompact  # Not full company object
    location: Optional[str]
    salary_range: Optional[str]  # Pre-formatted
    is_saved: bool
    is_applied: bool

    # Exclude: description, requirements, benefits
```

#### Pagination
```python
# Use cursor-based pagination (more efficient than offset)
def paginate_jobs(cursor: Optional[str] = None, limit: int = 20):
    query = session.query(Job)

    if cursor:
        decoded = decode_cursor(cursor)
        query = query.filter(Job.id < decoded.last_id)

    jobs = query.order_by(Job.id.desc()).limit(limit + 1).all()

    has_more = len(jobs) > limit
    if has_more:
        jobs = jobs[:limit]

    next_cursor = encode_cursor(jobs[-1].id) if has_more else None

    return jobs, next_cursor, has_more
```

### 3. Caching Strategies

#### Response Caching
```python
from functools import lru_cache
import hashlib

# Cache expensive computations
@lru_cache(maxsize=1000)
def calculate_match_score(user_id: int, job_id: int) -> float:
    # Expensive ML computation
    pass

# Cache database queries (with Redis)
import redis
cache = redis.Redis()

def get_job_with_cache(job_id: int):
    cache_key = f"job:{job_id}"

    # Try cache first
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)

    # Query database
    job = session.query(Job).get(job_id)

    # Store in cache (5 minute TTL)
    cache.setex(cache_key, 300, json.dumps(job.to_dict()))

    return job.to_dict()
```

#### Query Result Caching
```python
# Cache query results for frequently accessed data
class JobRepository:
    def get_active_jobs(self):
        cache_key = "active_jobs"

        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached)

        jobs = session.query(Job)\
            .filter(Job.status == JobStatus.OPEN)\
            .all()

        # Cache for 1 minute
        cache.setex(cache_key, 60, json.dumps([j.to_dict() for j in jobs]))

        return jobs
```

### 4. Async Processing

#### Background Tasks
```python
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def send_notification_email(user_id: int, notification_id: int):
    """Send notification email in background."""
    # Don't block API response for email sending
    pass

# In endpoint
@router.post("/applications")
async def submit_application(...):
    # Create application (fast)
    application = create_application(...)

    # Send email asynchronously (don't wait)
    send_notification_email.delay(user.id, notification.id)

    return application
```

### 5. Connection Pooling

#### Database Connection Pool
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Max 10 connections
    max_overflow=20,  # +20 temporary connections
    pool_pre_ping=True,  # Check connections before use
    pool_recycle=3600  # Recycle connections after 1 hour
)
```

---

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Response Time**: p50, p95, p99 for each endpoint
2. **Error Rate**: 4xx and 5xx errors per minute
3. **Throughput**: Requests per second
4. **Database**: Query time, connection pool usage
5. **CPU/Memory**: Server resource utilization

### Alert Thresholds

```yaml
alerts:
  - name: High Response Time
    condition: p95 > 1000ms for 5 minutes
    severity: warning

  - name: Very High Response Time
    condition: p95 > 2000ms for 2 minutes
    severity: critical

  - name: High Error Rate
    condition: error_rate > 5% for 5 minutes
    severity: critical

  - name: Database Connection Pool Exhausted
    condition: pool_usage > 90% for 2 minutes
    severity: critical
```

---

## Performance Testing Checklist

Before production deployment:

- [ ] All endpoints meet p95 response time targets
- [ ] All payloads meet size targets (<50KB)
- [ ] System handles 1000 concurrent users
- [ ] Database has appropriate indexes
- [ ] No N+1 query problems
- [ ] Connection pooling configured
- [ ] Caching implemented for hot paths
- [ ] Background jobs for expensive operations
- [ ] Monitoring and alerts configured
- [ ] Load testing completed successfully

---

## Tools and Resources

### Testing Tools
- **pytest-benchmark**: Python benchmark framework
- **Locust**: Load testing tool
- **Apache JMeter**: Alternative load testing
- **k6**: Modern load testing tool

### Monitoring Tools
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **New Relic**: APM monitoring
- **Datadog**: Application monitoring

### Database Tools
- **pg_stat_statements**: PostgreSQL query stats
- **EXPLAIN ANALYZE**: Query execution plans
- **pgAdmin**: Database management

---

## Next Steps

1. Run full performance test suite
2. Analyze results against targets
3. Identify and optimize bottlenecks
4. Re-test after optimizations
5. Document final performance characteristics
6. Setup production monitoring

For questions or issues, contact the performance team at perf@networking-ai.com
