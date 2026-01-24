"""Tests for background task queue."""

import asyncio

import pytest


class TestTaskQueue:
    """Test the background task queue."""

    def setup_method(self):
        from app.tasks import TaskQueue
        self.queue = TaskQueue(max_concurrent=2)

    def test_enqueue_and_execute(self):
        results = []

        async def sample_task(value):
            results.append(value)
            return value * 2

        async def _run():
            task_id = await self.queue.enqueue("test", sample_task, args=(42,))
            assert task_id is not None
            # Wait for execution
            await asyncio.sleep(0.2)
            status = self.queue.get_status(task_id)
            assert status is not None
            assert status["status"] == "completed"
            assert status["result"] == 84
            assert results == [42]

        asyncio.run(_run())

    def test_failed_task(self):
        async def failing_task():
            raise ValueError("intentional error")

        async def _run():
            task_id = await self.queue.enqueue("fail_test", failing_task)
            await asyncio.sleep(0.2)
            status = self.queue.get_status(task_id)
            assert status is not None
            assert status["status"] == "failed"
            assert "intentional error" in status["error"]

        asyncio.run(_run())

    def test_concurrency_limit(self):
        running = []
        max_concurrent = [0]

        async def slow_task(task_num):
            running.append(task_num)
            current = len(running)
            if current > max_concurrent[0]:
                max_concurrent[0] = current
            await asyncio.sleep(0.1)
            running.remove(task_num)

        async def _run():
            # Enqueue 5 tasks with max_concurrent=2
            for i in range(5):
                await self.queue.enqueue(f"concurrent_{i}", slow_task, args=(i,))
            # Wait for all to complete
            await asyncio.sleep(1.5)
            # Should never have exceeded 2 concurrent
            assert max_concurrent[0] <= 2

        asyncio.run(_run())

    def test_unknown_task_status(self):
        status = self.queue.get_status("nonexistent-id")
        assert status is None

    def test_get_queue_stats(self):
        async def noop():
            pass

        async def _run():
            await self.queue.enqueue("t1", noop)
            await self.queue.enqueue("t2", noop)
            await asyncio.sleep(0.2)
            stats = self.queue.get_queue_stats()
            assert "completed" in stats
            assert "running" in stats
            assert "pending" in stats
            assert stats["total_tracked"] >= 2

        asyncio.run(_run())

    def test_get_active_tasks(self):
        async def slow():
            await asyncio.sleep(1.0)

        async def _run():
            await self.queue.enqueue("active1", slow)
            await asyncio.sleep(0.05)
            active = self.queue.get_active_tasks()
            assert len(active) >= 1
            assert active[0]["status"] in ("pending", "running")

        asyncio.run(_run())
