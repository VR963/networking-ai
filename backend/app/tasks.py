"""Background Task System - Non-blocking AI operations.

PROBLEM SOLVED:
AI API calls take 2-10 seconds. Without background processing:
- HTTP requests block until AI responds
- 1000 concurrent users = 1000 blocked connections
- Server runs out of worker threads

SOLUTION:
- FastAPI BackgroundTasks for fire-and-forget operations
- Asyncio task queue for ordered processing
- Semaphore-controlled concurrency (max 10 concurrent AI calls)
- Task status tracking for long-running operations

USAGE:
    from app.tasks import task_queue

    # Fire-and-forget (governance cycles, training, etc.)
    task_id = await task_queue.enqueue("governance_cycle", governance_fn, args=())

    # Check status
    status = task_queue.get_status(task_id)
"""

import asyncio
import uuid
import time
import logging
from typing import Any, Callable, Optional
from datetime import datetime, timezone

from app.config import MAX_CONCURRENT_AI_CALLS


logger = logging.getLogger("cv2.tasks")


class TaskQueue:
    """Managed async task queue with concurrency control.

    Features:
    - Ordered execution within task types
    - Configurable concurrency limit (prevents API overload)
    - Task status tracking (pending, running, completed, failed)
    - Automatic cleanup of old task records
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_AI_CALLS):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: dict[str, dict] = {}  # task_id -> status
        self._max_history = 100  # Keep last N completed tasks

    async def enqueue(
        self,
        task_type: str,
        fn: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
    ) -> str:
        """Enqueue a background task.

        Args:
            task_type: Category of task (governance, training, marketing, etc.)
            fn: Async function to execute
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            task_id for status tracking
        """
        task_id = str(uuid.uuid4())[:12]
        self._tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }

        # Launch task with semaphore control
        asyncio.create_task(self._execute(task_id, fn, args, kwargs or {}))
        self._cleanup_old()

        return task_id

    def get_status(self, task_id: str) -> Optional[dict]:
        """Get current status of a task."""
        return self._tasks.get(task_id)

    def get_active_tasks(self) -> list[dict]:
        """Get all currently running tasks."""
        return [t for t in self._tasks.values() if t["status"] in ("pending", "running")]

    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        statuses = [t["status"] for t in self._tasks.values()]
        return {
            "pending": statuses.count("pending"),
            "running": statuses.count("running"),
            "completed": statuses.count("completed"),
            "failed": statuses.count("failed"),
            "total_tracked": len(self._tasks),
            "max_concurrent": self._semaphore._value,
        }

    async def _execute(
        self, task_id: str, fn: Callable, args: tuple, kwargs: dict
    ) -> None:
        """Execute a task with semaphore control."""
        try:
            async with self._semaphore:
                self._tasks[task_id]["status"] = "running"
                self._tasks[task_id]["started_at"] = datetime.now(timezone.utc).isoformat()

                logger.info("Task %s (%s) started", task_id, self._tasks[task_id]["type"])
                start = time.time()

                result = await fn(*args, **kwargs)

                duration = time.time() - start
                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                self._tasks[task_id]["result"] = self._safe_result(result)

                logger.info(
                    "Task %s completed in %.1fs", task_id, duration
                )
        except Exception as e:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._tasks[task_id]["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            logger.error("Task %s failed: %s", task_id, self._tasks[task_id]["error"])

    def _safe_result(self, result: Any) -> Any:
        """Ensure result is JSON-serializable and not too large."""
        if result is None:
            return None
        if isinstance(result, (str, int, float, bool)):
            return result
        if isinstance(result, dict):
            # Truncate large results
            import json
            serialized = json.dumps(result, default=str)
            if len(serialized) > 5000:
                return {"status": "completed", "summary": "Result too large to store"}
            return result
        return str(result)[:1000]

    def _cleanup_old(self) -> None:
        """Remove old completed/failed tasks beyond history limit."""
        completed = [
            (tid, t) for tid, t in self._tasks.items()
            if t["status"] in ("completed", "failed")
        ]
        if len(completed) > self._max_history:
            # Remove oldest
            completed.sort(key=lambda x: x[1].get("completed_at", ""))
            for tid, _ in completed[: len(completed) - self._max_history]:
                del self._tasks[tid]


task_queue = TaskQueue()
