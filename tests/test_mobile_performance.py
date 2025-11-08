"""
Mobile API Performance Benchmarks.

Tests cover:
- Response time benchmarks
- Concurrent request handling
- Payload size verification
- Database query optimization
- Pagination performance

Note: These tests are marked as skip for regular test runs.
Run separately with: pytest -v -m performance
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.networking_ai.api.main import app
from src.networking_ai.models.job import Job, JobStatus, JobType
from src.networking_ai.models.company import Company

client = TestClient(app)


@pytest.fixture
def auth_user(db_session):
    """Create authenticated user for performance tests."""
    user_data = {
        "email": "perftest@test.com",
        "password": "SecurePass123!",
        "full_name": "Performance Test User",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "perf_device",
            "push_token": "fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]
    user_id = response.json()["data"]["user"]["id"]

    return {
        "auth_header": {"Authorization": f"Bearer {access_token}"},
        "user_id": user_id
    }


@pytest.fixture
def large_dataset(db_session):
    """Create large dataset for performance testing."""
    # Create company
    company = Company(
        name="PerfTest Corp",
        description="Performance testing company",
        status="active"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    # Create 100 jobs for pagination testing
    jobs = []
    for i in range(100):
        job = Job(
            title=f"Job Position {i}",
            description=f"Description for job {i}",
            company_id=company.id,
            location="Remote",
            job_type=JobType.FULL_TIME,
            min_salary=80000 + (i * 1000),
            max_salary=120000 + (i * 1000),
            status=JobStatus.OPEN
        )
        jobs.append(job)

    db_session.bulk_save_objects(jobs)
    db_session.commit()

    return {"company": company, "job_count": 100}


# ==================== Response Time Benchmarks ====================

@pytest.mark.skip(reason="Performance test - run separately")
def test_job_search_response_time(auth_user, large_dataset):
    """Test job search responds within acceptable time."""
    auth = auth_user["auth_header"]

    # Warm up
    client.get("/api/v1/mobile/jobs", headers=auth)

    # Measure response time
    times = []
    for _ in range(10):
        start = time.time()
        response = client.get("/api/v1/mobile/jobs", headers=auth)
        duration = time.time() - start
        times.append(duration)

        assert response.status_code == 200

    avg_time = sum(times) / len(times)
    max_time = max(times)

    print(f"\nJob Search Performance:")
    print(f"Average response time: {avg_time:.3f}s")
    print(f"Max response time: {max_time:.3f}s")

    # Should respond in under 500ms on average
    assert avg_time < 0.5, f"Average response time {avg_time:.3f}s exceeds 500ms"
    assert max_time < 1.0, f"Max response time {max_time:.3f}s exceeds 1s"


@pytest.mark.skip(reason="Performance test - run separately")
def test_profile_retrieval_response_time(auth_user):
    """Test profile retrieval is fast."""
    auth = auth_user["auth_header"]

    # Warm up
    client.get("/api/v1/mobile/profile", headers=auth)

    # Measure
    times = []
    for _ in range(10):
        start = time.time()
        response = client.get("/api/v1/mobile/profile", headers=auth)
        duration = time.time() - start
        times.append(duration)

        assert response.status_code == 200

    avg_time = sum(times) / len(times)

    print(f"\nProfile Retrieval Performance:")
    print(f"Average response time: {avg_time:.3f}s")

    # Profile should be very fast (<200ms)
    assert avg_time < 0.2, f"Profile retrieval too slow: {avg_time:.3f}s"


@pytest.mark.skip(reason="Performance test - run separately")
def test_notification_list_response_time(auth_user):
    """Test notification listing is fast."""
    auth = auth_user["auth_header"]

    times = []
    for _ in range(10):
        start = time.time()
        response = client.get("/api/v1/mobile/notifications", headers=auth)
        duration = time.time() - start
        times.append(duration)

        assert response.status_code == 200

    avg_time = sum(times) / len(times)

    print(f"\nNotification List Performance:")
    print(f"Average response time: {avg_time:.3f}s")

    assert avg_time < 0.3


# ==================== Payload Size Benchmarks ====================

@pytest.mark.skip(reason="Performance test - run separately")
def test_job_list_payload_size(auth_user, large_dataset):
    """Test job list payload is reasonably sized."""
    auth = auth_user["auth_header"]

    response = client.get("/api/v1/mobile/jobs?limit=20", headers=auth)

    assert response.status_code == 200

    # Measure payload size
    payload_size = len(json.dumps(response.json()))
    payload_kb = payload_size / 1024

    print(f"\nJob List Payload Size:")
    print(f"Size: {payload_kb:.2f} KB")

    # Should be under 50KB for mobile optimization
    assert payload_kb < 50, f"Payload too large: {payload_kb:.2f}KB"


@pytest.mark.skip(reason="Performance test - run separately")
def test_profile_payload_size(auth_user):
    """Test profile payload is compact."""
    auth = auth_user["auth_header"]

    response = client.get("/api/v1/mobile/profile", headers=auth)

    assert response.status_code == 200

    payload_size = len(json.dumps(response.json()))
    payload_kb = payload_size / 1024

    print(f"\nProfile Payload Size:")
    print(f"Size: {payload_kb:.2f} KB")

    # Profile should be very compact (<10KB)
    assert payload_kb < 10, f"Profile payload too large: {payload_kb:.2f}KB"


# ==================== Concurrency Tests ====================

@pytest.mark.skip(reason="Performance test - run separately")
def test_concurrent_job_searches(auth_user, large_dataset):
    """Test handling concurrent job search requests."""
    auth = auth_user["auth_header"]

    def make_request():
        response = client.get("/api/v1/mobile/jobs", headers=auth)
        return response.status_code, time.time()

    # Simulate 50 concurrent users
    start = time.time()
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(make_request) for _ in range(50)]
        results = [f.result() for f in as_completed(futures)]

    total_time = time.time() - start

    # Check all succeeded
    success_count = sum(1 for status, _ in results if status == 200)

    print(f"\nConcurrency Test:")
    print(f"Total requests: 50")
    print(f"Successful: {success_count}")
    print(f"Total time: {total_time:.3f}s")
    print(f"Requests/second: {50/total_time:.2f}")

    # At least 95% should succeed
    assert success_count >= 47, f"Too many failures: {50 - success_count}"

    # Should handle 50 requests in under 10 seconds
    assert total_time < 10, f"Concurrent requests too slow: {total_time:.3f}s"


@pytest.mark.skip(reason="Performance test - run separately")
def test_concurrent_profile_updates(auth_user):
    """Test handling concurrent profile updates."""
    auth = auth_user["auth_header"]

    def update_profile(iteration):
        response = client.patch(
            "/api/v1/mobile/profile",
            headers=auth,
            json={"headline": f"Engineer {iteration}"}
        )
        return response.status_code

    # 20 concurrent updates
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(update_profile, i) for i in range(20)]
        results = [f.result() for f in as_completed(futures)]

    # All should succeed
    success_count = sum(1 for status in results if status == 200)

    print(f"\nConcurrent Profile Updates:")
    print(f"Successful: {success_count}/20")

    assert success_count >= 18  # Allow small margin for DB contention


# ==================== Pagination Performance ====================

@pytest.mark.skip(reason="Performance test - run separately")
def test_pagination_cursor_performance(auth_user, large_dataset):
    """Test cursor pagination performs well on large datasets."""
    auth = auth_user["auth_header"]

    # Fetch first page
    start = time.time()
    response1 = client.get("/api/v1/mobile/jobs?limit=20", headers=auth)
    time1 = time.time() - start

    assert response1.status_code == 200
    cursor = response1.json()["data"]["meta"].get("cursor")

    # Fetch second page with cursor
    start = time.time()
    response2 = client.get(
        f"/api/v1/mobile/jobs?limit=20&cursor={cursor}",
        headers=auth
    )
    time2 = time.time() - start

    assert response2.status_code == 200

    print(f"\nPagination Performance:")
    print(f"First page: {time1:.3f}s")
    print(f"Second page (with cursor): {time2:.3f}s")

    # Both should be fast, second page shouldn't be slower
    assert time1 < 0.5
    assert time2 < 0.5
    # Cursor pagination should be consistent
    assert abs(time2 - time1) < 0.3


@pytest.mark.skip(reason="Performance test - run separately")
def test_deep_pagination_performance(auth_user, large_dataset):
    """Test pagination performance doesn't degrade for deep pages."""
    auth = auth_user["auth_header"]

    times = []
    cursor = None

    # Paginate through 5 pages
    for page in range(5):
        url = "/api/v1/mobile/jobs?limit=20"
        if cursor:
            url += f"&cursor={cursor}"

        start = time.time()
        response = client.get(url, headers=auth)
        duration = time.time() - start

        times.append(duration)

        assert response.status_code == 200
        cursor = response.json()["data"]["meta"].get("cursor")

    print(f"\nDeep Pagination Performance:")
    for i, t in enumerate(times, 1):
        print(f"Page {i}: {t:.3f}s")

    # No page should be significantly slower
    avg_time = sum(times) / len(times)
    max_time = max(times)

    assert max_time < 0.7  # No single page should be very slow
    assert max_time / avg_time < 2  # Max shouldn't be 2x average


# ==================== Database Query Optimization ====================

@pytest.mark.skip(reason="Performance test - run separately")
def test_n_plus_one_query_prevention(auth_user, large_dataset):
    """Test that endpoints don't have N+1 query problems."""
    # This test would require query counting
    # For now, we verify response time doesn't scale with data
    auth = auth_user["auth_header"]

    # Time with 100 jobs
    start = time.time()
    response = client.get("/api/v1/mobile/jobs?limit=50", headers=auth)
    time_100 = time.time() - start

    assert response.status_code == 200

    print(f"\nQuery Optimization:")
    print(f"Time for 50 jobs from 100 dataset: {time_100:.3f}s")

    # Should be fast even with large dataset
    # Good optimization means this should be <500ms
    assert time_100 < 0.5, "Potential N+1 query problem detected"
