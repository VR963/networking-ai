"""
Background Task Manager.

Handles asynchronous task execution for computationally expensive operations
like AI matching, embedding generation, and batch processing.

Note: This is a simple threading-based implementation suitable for development
and light production use. For high-scale production, consider using Celery + Redis.
"""

import threading
import queue
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import traceback


class TaskStatus(str, Enum):
    """Background task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTask:
    """Represents a background task."""

    def __init__(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None
    ):
        """
        Initialize a background task.

        Args:
            task_id: Unique task identifier
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
        """
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = TaskStatus.PENDING
        self.result: Any = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def execute(self):
        """Execute the task."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
            print(f"[TASK] Task {self.task_id} completed successfully")
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            print(f"[TASK] Task {self.task_id} failed: {e}")
            traceback.print_exc()
        finally:
            self.completed_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BackgroundTaskManager:
    """
    Manages background task execution using a thread pool.

    Uses a queue-based approach with worker threads to process tasks asynchronously.
    """

    def __init__(self, num_workers: int = 3):
        """
        Initialize task manager.

        Args:
            num_workers: Number of worker threads
        """
        self.num_workers = num_workers
        self.task_queue: queue.Queue = queue.Queue()
        self.tasks: Dict[str, BackgroundTask] = {}
        self.workers: list = []
        self.running = False
        self._lock = threading.Lock()
        self._task_counter = 0

    def start(self):
        """Start worker threads."""
        if self.running:
            return

        self.running = True
        print(f"[TASK MANAGER] Starting {self.num_workers} worker threads...")

        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

        print("[TASK MANAGER] All workers started")

    def stop(self):
        """Stop all worker threads."""
        print("[TASK MANAGER] Stopping workers...")
        self.running = False

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        self.workers.clear()
        print("[TASK MANAGER] All workers stopped")

    def _worker_loop(self):
        """Worker thread main loop."""
        thread_name = threading.current_thread().name
        print(f"[{thread_name}] Worker started")

        while self.running:
            try:
                # Get task from queue (timeout to allow checking self.running)
                task = self.task_queue.get(timeout=1)

                print(f"[{thread_name}] Executing task {task.task_id}")
                task.execute()

                self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[{thread_name}] Worker error: {e}")
                traceback.print_exc()

        print(f"[{thread_name}] Worker stopped")

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        with self._lock:
            self._task_counter += 1
            return f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{self._task_counter}"

    def submit_task(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Submit a task for background execution.

        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            task_id: Optional custom task ID

        Returns:
            Task ID
        """
        if not self.running:
            self.start()

        task_id = task_id or self._generate_task_id()

        task = BackgroundTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs
        )

        with self._lock:
            self.tasks[task_id] = task

        self.task_queue.put(task)

        print(f"[TASK MANAGER] Submitted task {task_id}")

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task.

        Args:
            task_id: Task ID

        Returns:
            Task status dictionary or None if not found
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                return task.to_dict()
            return None

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tasks."""
        with self._lock:
            return {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            }

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Clean up old completed/failed tasks.

        Args:
            max_age_hours: Maximum age of tasks to keep
        """
        now = datetime.utcnow()
        to_remove = []

        with self._lock:
            for task_id, task in self.tasks.items():
                if task.completed_at:
                    age_hours = (now - task.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]

        if to_remove:
            print(f"[TASK MANAGER] Cleaned up {len(to_remove)} old tasks")


# Global task manager instance
task_manager = BackgroundTaskManager()


# ============================================================================
# Convenience Functions for Common Tasks
# ============================================================================

def run_matching_for_profile(profile_id: int, db_session_factory) -> Dict[str, Any]:
    """
    Background task: Run matching for a specific profile.

    Args:
        profile_id: Profile ID
        db_session_factory: Function that creates a new DB session

    Returns:
        Result dictionary
    """
    from .matching_service import create_matching_service

    print(f"[TASK] Starting matching for profile {profile_id}")

    # Create new database session for this thread
    db = db_session_factory()

    try:
        matching_service = create_matching_service(db)
        matches = matching_service.match_profile_to_jobs(
            profile_id=profile_id,
            limit=10,
            min_score=0.5
        )

        return {
            "profile_id": profile_id,
            "matches_created": len(matches),
            "match_ids": [m.id for m in matches]
        }

    finally:
        db.close()


def run_matching_for_job(job_id: int, db_session_factory) -> Dict[str, Any]:
    """
    Background task: Run matching for a specific job.

    Args:
        job_id: Job ID
        db_session_factory: Function that creates a new DB session

    Returns:
        Result dictionary
    """
    from .matching_service import create_matching_service

    print(f"[TASK] Starting matching for job {job_id}")

    # Create new database session for this thread
    db = db_session_factory()

    try:
        matching_service = create_matching_service(db)
        matches = matching_service.match_job_to_profiles(
            job_id=job_id,
            limit=20,
            min_score=0.5
        )

        return {
            "job_id": job_id,
            "matches_created": len(matches),
            "match_ids": [m.id for m in matches]
        }

    finally:
        db.close()


def run_batch_matching(db_session_factory) -> Dict[str, Any]:
    """
    Background task: Run batch matching for all profiles and jobs.

    Args:
        db_session_factory: Function that creates a new DB session

    Returns:
        Result dictionary
    """
    from .matching_service import create_matching_service

    print("[TASK] Starting batch matching for all entities")

    # Create new database session for this thread
    db = db_session_factory()

    try:
        matching_service = create_matching_service(db)
        results = matching_service.batch_match_all(
            limit_per_entity=10,
            min_score=0.5
        )

        return results

    finally:
        db.close()
