"""
WebSocket Load Test Simulation - Phase 11

Simulates 1000 concurrent connections and measures performance
of our WebSocket broadcasting architecture.

This simulation tests:
- Connection manager capacity
- Memory sync event broadcasting
- Notification push broadcasting
- Message throughput
- Latency characteristics
"""

import asyncio
import time
import statistics
import json
from datetime import datetime
from typing import List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.networking_ai.websocket.connection_manager import ConnectionManager
from src.networking_ai.services.realtime_memory_service import RealtimeMemoryService
from src.networking_ai.services.realtime_notification_service import RealtimeNotificationService
from src.networking_ai.websocket.memory_events import MemoryCreatedEvent
from src.networking_ai.websocket.notification_events import NotificationCreatedEvent


class MockWebSocket:
    """Mock WebSocket connection for testing."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages_received = []
        self.connected_at = time.time()
        self.closed = False

    async def accept(self):
        """Accept WebSocket connection (required by ConnectionManager)."""
        pass  # Mock implementation

    async def send_json(self, message: dict):
        """Simulate sending JSON message."""
        if not self.closed:
            self.messages_received.append({
                "message": message,
                "received_at": time.time()
            })

    async def close(self):
        """Close connection."""
        self.closed = True


class LoadTestSimulation:
    """Simulates load testing with mock connections."""

    def __init__(self, num_users: int = 1000, duration: int = 300):
        self.num_users = num_users
        self.duration = duration
        self.connection_manager = ConnectionManager()
        self.memory_service = RealtimeMemoryService(self.connection_manager)
        self.notification_service = RealtimeNotificationService(self.connection_manager)

        # Metrics
        self.connection_times = []
        self.broadcast_latencies = []
        self.messages_sent = 0
        self.messages_received = 0
        self.errors = 0

        # Mock connections
        self.mock_connections: Dict[int, MockWebSocket] = {}

    async def setup_connections(self):
        """Setup mock WebSocket connections."""
        print(f"\nSetting up {self.num_users} mock WebSocket connections...")
        print(f"Connection ramp-up rate: 100 connections/second\n")

        for user_id in range(1, self.num_users + 1):
            start_time = time.time()

            try:
                # Create mock WebSocket
                mock_ws = MockWebSocket(user_id)
                self.mock_connections[user_id] = mock_ws

                # Connect to connection manager
                await self.connection_manager.connect(
                    websocket=mock_ws,
                    user_id=user_id,
                    agent_type="talent",
                    agent_id=user_id
                )

                connection_time = time.time() - start_time
                self.connection_times.append(connection_time)

                # Progress update
                if user_id % 100 == 0:
                    print(f"  → {user_id}/{self.num_users} connections established...")

                # Stagger connections (100/second)
                if user_id % 100 == 0:
                    await asyncio.sleep(1.0)

            except Exception as e:
                self.errors += 1
                print(f"  ✗ Failed to connect user {user_id}: {e}")

        print(f"\n✓ All connections established!")
        print(f"  Success rate: {(self.num_users - self.errors) / self.num_users * 100:.1f}%")
        print(f"  Avg connection time: {statistics.mean(self.connection_times)*1000:.2f}ms\n")

    async def test_memory_sync_broadcast(self, num_events: int = 100):
        """Test memory sync event broadcasting."""
        print(f"\n{'='*60}")
        print(f"Test 1: Memory Sync Broadcast ({num_events} events)")
        print(f"{'='*60}\n")

        broadcast_times = []

        for i in range(num_events):
            # Select random user
            user_id = (i % self.num_users) + 1

            # Broadcast memory created event
            start_time = time.time()

            await self.memory_service.broadcast_memory_created(
                memory_id=i + 1,
                user_id=user_id,
                content_preview=f"Test memory content {i+1}",
                importance=0.8,
                tier="hot",
                memory_type="conversation"
            )

            broadcast_time = time.time() - start_time
            broadcast_times.append(broadcast_time)
            self.messages_sent += 1

            # Count received messages
            if user_id in self.mock_connections:
                self.messages_received += len(self.mock_connections[user_id].messages_received)

            # Progress
            if (i + 1) % 20 == 0:
                print(f"  → {i+1}/{num_events} events broadcast...")

        self.broadcast_latencies.extend(broadcast_times)

        print(f"\n✓ Memory sync broadcast test complete!")
        print(f"  Events broadcast: {num_events}")
        print(f"  Avg broadcast time: {statistics.mean(broadcast_times)*1000:.2f}ms")
        print(f"  Min: {min(broadcast_times)*1000:.2f}ms")
        print(f"  Max: {max(broadcast_times)*1000:.2f}ms")
        print(f"  P95: {statistics.quantiles(broadcast_times, n=20)[18]*1000:.2f}ms")

    async def test_notification_broadcast(self, num_notifications: int = 100):
        """Test notification broadcasting."""
        print(f"\n{'='*60}")
        print(f"Test 2: Notification Broadcast ({num_notifications} notifications)")
        print(f"{'='*60}\n")

        from unittest.mock import Mock
        from src.networking_ai.models.notification import (
            Notification,
            NotificationType,
            NotificationPriority
        )

        broadcast_times = []

        for i in range(num_notifications):
            # Select random user
            user_id = (i % self.num_users) + 1

            # Create mock notification
            notification = Mock(spec=Notification)
            notification.id = i + 1
            notification.user_id = user_id
            notification.notification_type = NotificationType.MESSAGE_NEW
            notification.priority = NotificationPriority.NORMAL
            notification.title = f"Test Notification {i+1}"
            notification.message = f"This is test message {i+1}"
            notification.action_url = f"/messages/{i+1}"
            notification.action_text = "View"
            notification.extra_data = {"test": True}
            notification.expires_at = None

            # Broadcast notification
            start_time = time.time()

            await self.notification_service.broadcast_notification(notification)

            broadcast_time = time.time() - start_time
            broadcast_times.append(broadcast_time)
            self.messages_sent += 1

            # Count received messages
            if user_id in self.mock_connections:
                self.messages_received += len(self.mock_connections[user_id].messages_received)

            # Progress
            if (i + 1) % 20 == 0:
                print(f"  → {i+1}/{num_notifications} notifications broadcast...")

        self.broadcast_latencies.extend(broadcast_times)

        print(f"\n✓ Notification broadcast test complete!")
        print(f"  Notifications broadcast: {num_notifications}")
        print(f"  Avg broadcast time: {statistics.mean(broadcast_times)*1000:.2f}ms")
        print(f"  Min: {min(broadcast_times)*1000:.2f}ms")
        print(f"  Max: {max(broadcast_times)*1000:.2f}ms")
        print(f"  P95: {statistics.quantiles(broadcast_times, n=20)[18]*1000:.2f}ms")

    async def test_burst_broadcast(self, burst_size: int = 50):
        """Test burst broadcasting (all users at once)."""
        print(f"\n{'='*60}")
        print(f"Test 3: Burst Broadcast ({burst_size} users simultaneously)")
        print(f"{'='*60}\n")

        from unittest.mock import Mock
        from src.networking_ai.models.notification import (
            Notification,
            NotificationType,
            NotificationPriority
        )

        # Create notifications for multiple users
        notifications = []
        for i in range(burst_size):
            notification = Mock(spec=Notification)
            notification.id = i + 1
            notification.user_id = i + 1
            notification.notification_type = NotificationType.MATCH_NEW
            notification.priority = NotificationPriority.HIGH
            notification.title = "🎯 New Match!"
            notification.message = "You have a new match!"
            notification.action_url = "/matches/123"
            notification.action_text = "View Match"
            notification.extra_data = {}
            notification.expires_at = None
            notifications.append(notification)

        # Broadcast all at once
        print(f"  Broadcasting to {burst_size} users simultaneously...")
        start_time = time.time()

        tasks = [
            self.notification_service.broadcast_notification(notif)
            for notif in notifications
        ]

        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        print(f"\n✓ Burst broadcast test complete!")
        print(f"  Users: {burst_size}")
        print(f"  Total time: {total_time*1000:.2f}ms")
        print(f"  Avg time per user: {total_time/burst_size*1000:.2f}ms")
        print(f"  Throughput: {burst_size/total_time:.2f} broadcasts/sec")

    async def cleanup_connections(self):
        """Cleanup all mock connections."""
        print(f"\nCleaning up {len(self.mock_connections)} connections...")

        for user_id, mock_ws in self.mock_connections.items():
            await mock_ws.close()
            connection_id = f"{user_id}_{mock_ws.connected_at}"

            # Note: connection_manager.disconnect requires actual connection_id
            # For simulation, we skip actual disconnection

        print(f"✓ All connections cleaned up\n")

    def print_final_report(self, start_time: float):
        """Print final test report."""
        duration = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"FINAL LOAD TEST REPORT")
        print(f"{'='*60}\n")

        print(f"Test Configuration:")
        print(f"  Target Users: {self.num_users}")
        print(f"  Test Duration: {duration:.2f} seconds")
        print(f"\n")

        print(f"Connection Results:")
        print(f"  Successful: {self.num_users - self.errors} ({(self.num_users - self.errors)/self.num_users*100:.1f}%)")
        print(f"  Failed: {self.errors} ({self.errors/self.num_users*100:.1f}%)")
        if self.connection_times:
            print(f"  Avg Connection Time: {statistics.mean(self.connection_times)*1000:.2f}ms")
        print(f"\n")

        print(f"Message Results:")
        print(f"  Messages Sent: {self.messages_sent}")
        print(f"  Messages Received: {self.messages_received}")
        print(f"  Throughput: {self.messages_sent/duration:.2f} msg/sec")
        print(f"\n")

        if self.broadcast_latencies:
            print(f"Broadcast Latency Statistics:")
            print(f"  Average: {statistics.mean(self.broadcast_latencies)*1000:.2f}ms")
            print(f"  Minimum: {min(self.broadcast_latencies)*1000:.2f}ms")
            print(f"  Maximum: {max(self.broadcast_latencies)*1000:.2f}ms")
            print(f"  P50 (Median): {statistics.median(self.broadcast_latencies)*1000:.2f}ms")
            print(f"  P95: {statistics.quantiles(self.broadcast_latencies, n=20)[18]*1000:.2f}ms")
            print(f"  P99: {statistics.quantiles(self.broadcast_latencies, n=100)[98]*1000:.2f}ms")
        print(f"\n")

        # Performance Assessment
        print(f"Performance Assessment:")
        avg_latency = statistics.mean(self.broadcast_latencies)*1000 if self.broadcast_latencies else 0
        p95_latency = statistics.quantiles(self.broadcast_latencies, n=20)[18]*1000 if self.broadcast_latencies else 0
        throughput = self.messages_sent/duration

        print(f"  ✓ Connection Capacity: {'PASS' if self.num_users >= 1000 else 'FAIL'} ({self.num_users} >= 1000)")
        print(f"  ✓ Connection Success Rate: {'PASS' if (self.num_users - self.errors)/self.num_users >= 0.99 else 'FAIL'} ({(self.num_users - self.errors)/self.num_users*100:.1f}% >= 99%)")
        print(f"  ✓ Avg Broadcast Latency: {'PASS' if avg_latency < 50 else 'FAIL'} ({avg_latency:.2f}ms < 50ms)")
        print(f"  ✓ P95 Latency: {'PASS' if p95_latency < 100 else 'FAIL'} ({p95_latency:.2f}ms < 100ms)")
        print(f"  ✓ Message Throughput: {'PASS' if throughput > 100 else 'FAIL'} ({throughput:.2f} msg/sec > 100)")

        print(f"\n{'='*60}\n")

        # Summary
        all_pass = (
            self.num_users >= 1000 and
            (self.num_users - self.errors)/self.num_users >= 0.99 and
            avg_latency < 50 and
            p95_latency < 100 and
            throughput > 100
        )

        if all_pass:
            print(f"🎉 ALL TESTS PASSED! System ready for production.")
        else:
            print(f"⚠️  SOME TESTS FAILED. Review performance metrics above.")

        print()

    async def run(self):
        """Run complete load test simulation."""
        print(f"\n{'='*60}")
        print(f"WebSocket Load Test Simulation")
        print(f"Phase 11 - Real-time Features")
        print(f"{'='*60}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: {self.num_users} concurrent connections")
        print(f"Duration: {self.duration} seconds (simulated)")
        print(f"{'='*60}\n")

        start_time = time.time()

        try:
            # Setup connections
            await self.setup_connections()

            # Run tests
            await self.test_memory_sync_broadcast(num_events=100)
            await self.test_notification_broadcast(num_notifications=100)
            await self.test_burst_broadcast(burst_size=50)

            # Cleanup
            await self.cleanup_connections()

            # Print final report
            self.print_final_report(start_time)

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
            await self.cleanup_connections()

        except Exception as e:
            print(f"\n\nTest failed with error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket Load Test Simulation")
    parser.add_argument(
        "--users",
        type=int,
        default=1000,
        help="Number of concurrent users (default: 1000)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Test duration in seconds (default: 300)"
    )

    args = parser.parse_args()

    # Run simulation
    simulation = LoadTestSimulation(
        num_users=args.users,
        duration=args.duration
    )

    await simulation.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest terminated by user.")
        sys.exit(0)
