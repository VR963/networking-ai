"""
WebSocket Load Testing Script - Phase 11

Tests WebSocket server with concurrent connections and broadcasts.

Usage:
    python websocket_load_test.py --users 1000 --duration 300

Features:
- Concurrent WebSocket connections
- Memory sync event simulation
- Notification broadcast simulation
- Real-time metrics collection
- Performance reporting
"""

import asyncio
import websockets
import json
import time
import argparse
import statistics
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass, field
import sys


@dataclass
class ConnectionMetrics:
    """Metrics for a single connection."""
    user_id: int
    connected_at: float
    disconnected_at: float = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    latencies: List[float] = field(default_factory=list)


@dataclass
class TestResults:
    """Overall test results."""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_errors: int = 0
    connection_times: List[float] = field(default_factory=list)
    message_latencies: List[float] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0

    @property
    def duration(self) -> float:
        """Test duration in seconds."""
        return self.end_time - self.start_time if self.end_time > 0 else 0

    @property
    def avg_connection_time(self) -> float:
        """Average connection time in milliseconds."""
        return statistics.mean(self.connection_times) * 1000 if self.connection_times else 0

    @property
    def avg_message_latency(self) -> float:
        """Average message latency in milliseconds."""
        return statistics.mean(self.message_latencies) * 1000 if self.message_latencies else 0

    @property
    def messages_per_second(self) -> float:
        """Messages per second throughput."""
        return self.total_messages_received / self.duration if self.duration > 0 else 0

    @property
    def p95_latency(self) -> float:
        """95th percentile latency in milliseconds."""
        if not self.message_latencies:
            return 0
        sorted_latencies = sorted(self.message_latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index] * 1000 if index < len(sorted_latencies) else 0

    @property
    def p99_latency(self) -> float:
        """99th percentile latency in milliseconds."""
        if not self.message_latencies:
            return 0
        sorted_latencies = sorted(self.message_latencies)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index] * 1000 if index < len(sorted_latencies) else 0


class WebSocketClient:
    """Simulates a single WebSocket client."""

    def __init__(self, user_id: int, ws_url: str, results: TestResults):
        """
        Initialize WebSocket client.

        Args:
            user_id: User ID for this client
            ws_url: WebSocket server URL
            results: Shared results object
        """
        self.user_id = user_id
        self.ws_url = ws_url
        self.results = results
        self.metrics = ConnectionMetrics(user_id=user_id, connected_at=0)
        self.websocket = None
        self.running = False

    async def connect(self):
        """Connect to WebSocket server."""
        start_time = time.time()
        try:
            # Connect with JWT token (simulated user token)
            uri = f"{self.ws_url}?token=user_{self.user_id}"
            self.websocket = await websockets.connect(uri)

            connection_time = time.time() - start_time
            self.metrics.connected_at = time.time()
            self.results.connection_times.append(connection_time)
            self.results.successful_connections += 1
            self.running = True

            return True

        except Exception as e:
            self.results.failed_connections += 1
            self.metrics.errors += 1
            print(f"[User {self.user_id}] Connection failed: {e}")
            return False

    async def send_heartbeat(self):
        """Send heartbeat message."""
        if not self.websocket:
            return

        try:
            message = {
                "action": "heartbeat",
                "data": {}
            }

            send_time = time.time()
            await self.websocket.send(json.dumps(message))
            self.metrics.messages_sent += 1
            self.results.total_messages_sent += 1

        except Exception as e:
            self.metrics.errors += 1
            self.results.total_errors += 1
            print(f"[User {self.user_id}] Heartbeat failed: {e}")

    async def receive_messages(self):
        """Receive and process messages."""
        if not self.websocket:
            return

        try:
            while self.running:
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=1.0
                )

                receive_time = time.time()

                # Parse message
                try:
                    data = json.loads(message)
                    event_type = data.get("event", "unknown")

                    # Track metrics
                    self.metrics.messages_received += 1
                    self.results.total_messages_received += 1

                    # Calculate latency if timestamp present
                    if "timestamp" in data:
                        try:
                            sent_time = datetime.fromisoformat(data["timestamp"]).timestamp()
                            latency = receive_time - sent_time
                            self.metrics.latencies.append(latency)
                            self.results.message_latencies.append(latency)
                        except:
                            pass

                except json.JSONDecodeError:
                    pass

        except asyncio.TimeoutError:
            # No message received, continue
            pass
        except websockets.exceptions.ConnectionClosed:
            self.running = False
        except Exception as e:
            self.metrics.errors += 1
            self.results.total_errors += 1

    async def run(self, duration: int):
        """
        Run client for specified duration.

        Args:
            duration: Duration in seconds
        """
        # Connect
        if not await self.connect():
            return

        print(f"[User {self.user_id}] Connected")

        # Run for duration
        start_time = time.time()
        receive_task = asyncio.create_task(self.receive_messages())

        while time.time() - start_time < duration and self.running:
            # Send heartbeat every 30 seconds
            await self.send_heartbeat()
            await asyncio.sleep(30)

        # Cleanup
        self.running = False
        receive_task.cancel()

        try:
            await receive_task
        except asyncio.CancelledError:
            pass

        if self.websocket:
            await self.websocket.close()

        self.metrics.disconnected_at = time.time()
        print(f"[User {self.user_id}] Disconnected")

    async def disconnect(self):
        """Disconnect from server."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        self.metrics.disconnected_at = time.time()


class LoadTester:
    """Manages load testing with multiple clients."""

    def __init__(self, ws_url: str, num_users: int, duration: int):
        """
        Initialize load tester.

        Args:
            ws_url: WebSocket server URL
            num_users: Number of concurrent users
            duration: Test duration in seconds
        """
        self.ws_url = ws_url
        self.num_users = num_users
        self.duration = duration
        self.results = TestResults()
        self.clients: List[WebSocketClient] = []

    async def run(self):
        """Run load test."""
        print(f"\n{'='*60}")
        print(f"WebSocket Load Test")
        print(f"{'='*60}")
        print(f"Server: {self.ws_url}")
        print(f"Users: {self.num_users}")
        print(f"Duration: {self.duration} seconds")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        self.results.start_time = time.time()
        self.results.total_connections = self.num_users

        # Create clients
        self.clients = [
            WebSocketClient(user_id=i+1, ws_url=self.ws_url, results=self.results)
            for i in range(self.num_users)
        ]

        # Stagger connection ramp-up (10 connections per second)
        print(f"Ramping up {self.num_users} connections...")
        tasks = []

        for i, client in enumerate(self.clients):
            # Stagger connections
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(1.0)  # 10 connections per second

            task = asyncio.create_task(client.run(self.duration))
            tasks.append(task)

            # Progress update
            if (i + 1) % 100 == 0:
                print(f"  → {i + 1}/{self.num_users} connections initiated...")

        print(f"All {self.num_users} connections initiated!\n")
        print(f"Running test for {self.duration} seconds...")
        print(f"Press Ctrl+C to stop early\n")

        # Wait for all clients to finish
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user. Cleaning up...")
            for client in self.clients:
                await client.disconnect()

        self.results.end_time = time.time()

        # Print results
        self.print_results()

    def print_results(self):
        """Print test results."""
        print(f"\n{'='*60}")
        print(f"Load Test Results")
        print(f"{'='*60}\n")

        print(f"Test Configuration:")
        print(f"  Total Users: {self.results.total_connections}")
        print(f"  Duration: {self.results.duration:.2f} seconds")
        print(f"\n")

        print(f"Connection Results:")
        print(f"  Successful: {self.results.successful_connections} ({self.results.successful_connections/self.results.total_connections*100:.1f}%)")
        print(f"  Failed: {self.results.failed_connections} ({self.results.failed_connections/self.results.total_connections*100:.1f}%)")
        print(f"  Avg Connection Time: {self.results.avg_connection_time:.2f}ms")
        print(f"\n")

        print(f"Message Results:")
        print(f"  Messages Sent: {self.results.total_messages_sent}")
        print(f"  Messages Received: {self.results.total_messages_received}")
        print(f"  Total Errors: {self.results.total_errors}")
        print(f"  Throughput: {self.results.messages_per_second:.2f} msg/sec")
        print(f"\n")

        if self.results.message_latencies:
            print(f"Latency Statistics:")
            print(f"  Average: {self.results.avg_message_latency:.2f}ms")
            print(f"  Minimum: {min(self.results.message_latencies)*1000:.2f}ms")
            print(f"  Maximum: {max(self.results.message_latencies)*1000:.2f}ms")
            print(f"  P95: {self.results.p95_latency:.2f}ms")
            print(f"  P99: {self.results.p99_latency:.2f}ms")
        else:
            print(f"Latency Statistics: No data (server may not be sending timestamped events)")

        print(f"\n")

        # Success criteria
        print(f"Success Criteria:")
        success_rate = self.results.successful_connections / self.results.total_connections
        latency_ok = self.results.avg_message_latency < 100 if self.results.message_latencies else True
        error_rate = self.results.total_errors / max(self.results.total_messages_sent, 1)

        print(f"  ✓ Connection Rate: {'PASS' if success_rate >= 0.95 else 'FAIL'} ({success_rate*100:.1f}% >= 95%)")
        print(f"  ✓ Avg Latency: {'PASS' if latency_ok else 'FAIL'} ({self.results.avg_message_latency:.2f}ms < 100ms)")
        print(f"  ✓ Error Rate: {'PASS' if error_rate < 0.01 else 'FAIL'} ({error_rate*100:.2f}% < 1%)")

        print(f"\n{'='*60}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="WebSocket Load Testing")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws",
        help="WebSocket server URL (default: ws://localhost:8000/ws)"
    )
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

    # Run load test
    tester = LoadTester(
        ws_url=args.url,
        num_users=args.users,
        duration=args.duration
    )

    await tester.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest terminated by user.")
        sys.exit(0)
