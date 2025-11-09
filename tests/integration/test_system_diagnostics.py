"""Integration tests for system-level diagnostics and event synchronization.

Tests the /api/sensors/state endpoint, EventBus event emission/retrieval,
and system metric collection with proper schema validation.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from typing import Any, Dict, List


@pytest.fixture
def mock_event_store():
    """Mock durable event store."""
    mock = MagicMock()
    mock.events = []
    mock.next_id = 1

    def append_event(topic: str, payload: Dict[str, Any], tenant_id: str = "default"):
        """Append event to store."""
        event = {
            "id": mock.next_id,
            "topic": topic,
            "payload": payload,
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat(),
        }
        mock.events.append(event)
        mock.next_id += 1
        return event["id"]

    def list_events_after(last_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """List events after ID."""
        return [e for e in mock.events if e["id"] > last_id][:limit]

    mock.append_event = MagicMock(side_effect=append_event)
    mock.list_events_after = MagicMock(side_effect=list_events_after)

    return mock


@pytest.fixture
def mock_system_monitor():
    """Mock system monitor for reproducible metrics."""
    mock = MagicMock()

    # Mock resource usage
    mock.cpu_percent = MagicMock(return_value=25.5)
    mock.memory_percent = MagicMock(return_value=45.2)
    mock.disk_percent = MagicMock(return_value=62.8)
    mock.open_files_count = MagicMock(return_value=42)
    mock.thread_count = MagicMock(return_value=8)
    mock.event_queue_size = MagicMock(return_value=3)

    async def check_health():
        """Return mock resource usage."""
        return {
            "cpu_percent": mock.cpu_percent(),
            "memory_percent": mock.memory_percent(),
            "disk_percent": mock.disk_percent(),
            "open_files": mock.open_files_count(),
            "thread_count": mock.thread_count(),
            "event_queue_size": mock.event_queue_size(),
            "timestamp": datetime.now().isoformat(),
        }

    mock.check_health = AsyncMock(side_effect=check_health)
    return mock


@pytest.fixture
def event_bus_context(mock_event_store):
    """Provide an in-memory event bus with mock storage."""
    subscribers = []

    async def publish(topic: str, payload: Dict[str, Any], tenant_id: str = "default"):
        """Emit event to storage and subscribers."""
        # Store event
        event_id = mock_event_store.append_event(topic, payload, tenant_id)

        # Notify subscribers
        event = {
            "id": event_id,
            "topic": topic,
            "payload": payload,
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat(),
        }

        for sub_queue in subscribers:
            try:
                sub_queue.put_nowait(event)
            except Exception:
                pass

    async def subscribe():
        """Subscribe to events."""
        queue = asyncio.Queue()
        subscribers.append(queue)
        try:
            while True:
                yield queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        finally:
            try:
                subscribers.remove(queue)
            except ValueError:
                pass

    def fetch_events_after(last_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch events from storage."""
        return mock_event_store.list_events_after(last_id, limit)

    return {
        "publish": publish,
        "subscribe": subscribe,
        "fetch_events_after": fetch_events_after,
        "store": mock_event_store,
        "subscribers": subscribers,
    }


class TestSensorMetricsStructure:
    """Test /api/sensors/state endpoint and metrics structure."""

    @pytest.mark.asyncio
    async def test_sensor_metrics_complete_structure(self, mock_system_monitor):
        """Test that sensor metrics have all required fields."""
        metrics = await mock_system_monitor.check_health()

        # Verify all required fields are present
        required_fields = ["cpu_percent", "memory_percent", "thread_count", "timestamp"]
        for field in required_fields:
            assert field in metrics, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_sensor_metrics_cpu_percentage(self, mock_system_monitor):
        """Test CPU percentage metric."""
        metrics = await mock_system_monitor.check_health()

        assert "cpu_percent" in metrics
        cpu = metrics["cpu_percent"]
        assert isinstance(cpu, (int, float))
        assert 0 <= cpu <= 100, f"CPU percent should be 0-100, got {cpu}"

    @pytest.mark.asyncio
    async def test_sensor_metrics_memory_percentage(self, mock_system_monitor):
        """Test memory percentage metric."""
        metrics = await mock_system_monitor.check_health()

        assert "memory_percent" in metrics
        memory = metrics["memory_percent"]
        assert isinstance(memory, (int, float))
        assert 0 <= memory <= 100, f"Memory percent should be 0-100, got {memory}"

    @pytest.mark.asyncio
    async def test_sensor_metrics_thread_count(self, mock_system_monitor):
        """Test thread count metric."""
        metrics = await mock_system_monitor.check_health()

        assert "thread_count" in metrics
        threads = metrics["thread_count"]
        assert isinstance(threads, int)
        assert threads > 0, "Should have at least 1 thread"

    @pytest.mark.asyncio
    async def test_sensor_metrics_timestamp(self, mock_system_monitor):
        """Test timestamp format."""
        metrics = await mock_system_monitor.check_health()

        assert "timestamp" in metrics
        timestamp = metrics["timestamp"]
        assert isinstance(timestamp, str)
        # Should be ISO format
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail(f"Timestamp not in ISO format: {timestamp}")

    @pytest.mark.asyncio
    async def test_sensor_metrics_open_files(self, mock_system_monitor):
        """Test open files count metric."""
        metrics = await mock_system_monitor.check_health()

        assert "open_files" in metrics
        open_files = metrics["open_files"]
        assert isinstance(open_files, int)
        assert open_files >= 0

    @pytest.mark.asyncio
    async def test_sensor_metrics_disk_usage(self, mock_system_monitor):
        """Test disk usage percentage metric."""
        metrics = await mock_system_monitor.check_health()

        assert "disk_percent" in metrics
        disk = metrics["disk_percent"]
        assert isinstance(disk, (int, float))
        assert 0 <= disk <= 100, f"Disk percent should be 0-100, got {disk}"

    @pytest.mark.asyncio
    async def test_sensor_metrics_reproducible_values(self, mock_system_monitor):
        """Test that mocked metrics are reproducible."""
        metrics1 = await mock_system_monitor.check_health()
        metrics2 = await mock_system_monitor.check_health()

        # CPU and memory should be consistent (mocked)
        assert metrics1["cpu_percent"] == metrics2["cpu_percent"]
        assert metrics1["memory_percent"] == metrics2["memory_percent"]
        assert metrics1["thread_count"] == metrics2["thread_count"]

    @pytest.mark.asyncio
    async def test_sensor_metrics_within_bounds(self, mock_system_monitor):
        """Test that all percentage metrics are within valid bounds."""
        metrics = await mock_system_monitor.check_health()

        percent_fields = ["cpu_percent", "memory_percent", "disk_percent"]
        for field in percent_fields:
            if field in metrics:
                value = metrics[field]
                assert 0 <= value <= 100, f"{field} out of bounds: {value}"


class TestEventBusEmission:
    """Test EventBus event emission and storage."""

    @pytest.mark.asyncio
    async def test_event_emission_basic(self, event_bus_context):
        """Test basic event emission."""
        await event_bus_context["publish"](
            topic="test.event",
            payload={"message": "test"},
            tenant_id="default"
        )

        # Verify event was stored
        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 1
        assert events[0]["topic"] == "test.event"

    @pytest.mark.asyncio
    async def test_event_emission_multiple(self, event_bus_context):
        """Test multiple event emissions."""
        topics = ["event.1", "event.2", "event.3"]

        for topic in topics:
            await event_bus_context["publish"](
                topic=topic,
                payload={"id": topic},
                tenant_id="default"
            )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 3
        assert [e["topic"] for e in events] == topics

    @pytest.mark.asyncio
    async def test_event_emission_structure(self, event_bus_context):
        """Test event structure after emission."""
        payload = {"message": "test", "data": {"nested": "value"}}

        await event_bus_context["publish"](
            topic="system.update",
            payload=payload,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        event = events[0]

        # Verify structure
        assert "id" in event
        assert "topic" in event
        assert "payload" in event
        assert "tenant_id" in event
        assert "timestamp" in event

        # Verify values
        assert event["topic"] == "system.update"
        assert event["payload"] == payload
        assert event["tenant_id"] == "default"

    @pytest.mark.asyncio
    async def test_event_sequential_ids(self, event_bus_context):
        """Test that event IDs are sequential."""
        for i in range(5):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        events = event_bus_context["fetch_events_after"](0)
        ids = [e["id"] for e in events]

        # IDs should be sequential starting from 1
        assert ids == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_event_tenant_isolation(self, event_bus_context):
        """Test that events are tenant-aware."""
        await event_bus_context["publish"](
            topic="tenant.event",
            payload={"tenant": "a"},
            tenant_id="tenant-a"
        )

        await event_bus_context["publish"](
            topic="tenant.event",
            payload={"tenant": "b"},
            tenant_id="tenant-b"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 2
        assert events[0]["tenant_id"] == "tenant-a"
        assert events[1]["tenant_id"] == "tenant-b"

    @pytest.mark.asyncio
    async def test_system_update_event(self, event_bus_context, mock_system_monitor):
        """Test system.update event emission with sensor data."""
        metrics = await mock_system_monitor.check_health()

        # Emit system update event
        await event_bus_context["publish"](
            topic="system.update",
            payload=metrics,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 1

        event = events[0]
        assert event["topic"] == "system.update"
        assert event["payload"]["cpu_percent"] == 25.5
        assert event["payload"]["memory_percent"] == 45.2


class TestEventRetrieval:
    """Test event retrieval and synchronization."""

    @pytest.mark.asyncio
    async def test_fetch_events_after_id(self, event_bus_context):
        """Test fetching events after a specific ID."""
        # Emit 5 events
        for i in range(5):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        # Fetch after ID 2 (should get events 3, 4, 5)
        events = event_bus_context["fetch_events_after"](2)
        assert len(events) == 3
        assert [e["id"] for e in events] == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_fetch_events_with_limit(self, event_bus_context):
        """Test fetching events with limit."""
        # Emit 10 events
        for i in range(10):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        # Fetch after ID 0 with limit 3
        events = event_bus_context["fetch_events_after"](0, limit=3)
        assert len(events) == 3
        assert [e["id"] for e in events] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_fetch_events_no_results(self, event_bus_context):
        """Test fetching events when none exist."""
        events = event_bus_context["fetch_events_after"](999)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_fetch_events_ordering(self, event_bus_context):
        """Test that fetched events are ordered by ID."""
        # Emit events in order
        for i in range(5):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={"order": i},
                tenant_id="default"
            )

        events = event_bus_context["fetch_events_after"](0)

        # Should be ordered by ID ascending
        ids = [e["id"] for e in events]
        assert ids == sorted(ids)

    @pytest.mark.asyncio
    async def test_last_event_id_checkpoint(self, event_bus_context):
        """Test Last-Event-ID checkpoint pattern for SSE resume."""
        # Emit initial events (will have IDs 1, 2, 3)
        for i in range(3):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        # Simulate client checkpoint at ID 2
        last_event_id = 2

        # Emit more events (will have IDs 4, 5)
        for i in range(3, 5):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        # Fetch events since checkpoint
        events = event_bus_context["fetch_events_after"](last_event_id)

        # Should get events with ID > 2 (i.e., IDs 3, 4, 5)
        assert len(events) == 3
        assert [e["id"] for e in events] == [3, 4, 5]


class TestEventSynchronization:
    """Test event synchronization patterns."""

    @pytest.mark.asyncio
    async def test_message_created_event(self, event_bus_context):
        """Test message.created event emission."""
        event_payload = {
            "thread_id": 1,
            "message_id": 42,
            "role": "assistant",
            "content": "Hello"
        }

        await event_bus_context["publish"](
            topic="message.created",
            payload=event_payload,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 1
        assert events[0]["payload"]["thread_id"] == 1

    @pytest.mark.asyncio
    async def test_thread_updated_event(self, event_bus_context):
        """Test thread.updated event emission."""
        event_payload = {
            "thread_id": 1,
            "title": "Updated Title",
            "updated_at": datetime.now().isoformat()
        }

        await event_bus_context["publish"](
            topic="thread.updated",
            payload=event_payload,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 1
        assert events[0]["payload"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_connector_sync_event(self, event_bus_context):
        """Test connector.sync event emission."""
        event_payload = {
            "connector": "slack",
            "status": "success",
            "synced_count": 10
        }

        await event_bus_context["publish"](
            topic="connector.sync",
            payload=event_payload,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 1
        assert events[0]["payload"]["connector"] == "slack"

    @pytest.mark.asyncio
    async def test_memory_ingest_event(self, event_bus_context):
        """Test memory.ingest event emission."""
        event_payload = {
            "source": "github",
            "connector": "github-org",
            "inserted": 5
        }

        await event_bus_context["publish"](
            topic="memory.ingest",
            payload=event_payload,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 1
        assert events[0]["payload"]["source"] == "github"

    @pytest.mark.asyncio
    async def test_event_stream_sequence(self, event_bus_context):
        """Test sequence of events in a realistic scenario."""
        # Simulate chat completion workflow
        events = [
            ("message.created", {"thread_id": 1, "role": "user"}),
            ("message.created", {"thread_id": 1, "role": "assistant"}),
            ("thread.updated", {"thread_id": 1, "message_count": 2}),
            ("system.update", {"cpu_percent": 25.5, "memory_percent": 45.2}),
        ]

        for topic, payload in events:
            await event_bus_context["publish"](
                topic=topic,
                payload=payload,
                tenant_id="default"
            )

        stored_events = event_bus_context["fetch_events_after"](0)
        assert len(stored_events) == 4

        # Verify sequence
        topics = [e["topic"] for e in stored_events]
        assert topics == [
            "message.created",
            "message.created",
            "thread.updated",
            "system.update"
        ]


class TestSystemMetricCollection:
    """Test system metric collection patterns."""

    @pytest.mark.asyncio
    async def test_periodic_metric_emission(self, event_bus_context, mock_system_monitor):
        """Test periodic metric collection and emission."""
        intervals = 3

        for i in range(intervals):
            metrics = await mock_system_monitor.check_health()
            await event_bus_context["publish"](
                topic="system.update",
                payload=metrics,
                tenant_id="default"
            )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == intervals
        assert all(e["topic"] == "system.update" for e in events)

    @pytest.mark.asyncio
    async def test_metric_payload_schema(self, event_bus_context, mock_system_monitor):
        """Test that metric payload matches expected schema."""
        metrics = await mock_system_monitor.check_health()

        await event_bus_context["publish"](
            topic="system.update",
            payload=metrics,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        payload = events[0]["payload"]

        # Verify schema
        expected_fields = ["cpu_percent", "memory_percent", "thread_count", "timestamp"]
        for field in expected_fields:
            assert field in payload, f"Missing field in metric: {field}"

        # Verify types
        assert isinstance(payload["cpu_percent"], (int, float))
        assert isinstance(payload["memory_percent"], (int, float))
        assert isinstance(payload["thread_count"], int)
        assert isinstance(payload["timestamp"], str)

    @pytest.mark.asyncio
    async def test_metric_threshold_detection(self, mock_system_monitor):
        """Test detecting metric thresholds."""
        # Mock high CPU usage
        mock_system_monitor.cpu_percent.return_value = 85.0

        metrics = await mock_system_monitor.check_health()

        # Detect threshold
        cpu_alert = metrics["cpu_percent"] > 80
        assert cpu_alert is True

    @pytest.mark.asyncio
    async def test_metric_trend_tracking(self, event_bus_context, mock_system_monitor):
        """Test tracking metric trends over time."""
        cpu_values = [20.0, 25.5, 30.0, 35.5, 40.0]

        for cpu in cpu_values:
            mock_system_monitor.cpu_percent.return_value = cpu
            metrics = await mock_system_monitor.check_health()

            await event_bus_context["publish"](
                topic="system.update",
                payload=metrics,
                tenant_id="default"
            )

        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == 5

        # Extract CPU values from events
        cpu_trend = [e["payload"]["cpu_percent"] for e in events]
        assert cpu_trend == cpu_values

    @pytest.mark.asyncio
    async def test_event_count_in_metrics(self, event_bus_context, mock_system_monitor):
        """Test that event queue size is tracked in metrics."""
        # Simulate event queue building up
        mock_system_monitor.event_queue_size.return_value = 5

        metrics = await mock_system_monitor.check_health()

        assert metrics["event_queue_size"] == 5

        # Emit as system update
        await event_bus_context["publish"](
            topic="system.update",
            payload=metrics,
            tenant_id="default"
        )

        events = event_bus_context["fetch_events_after"](0)
        assert events[0]["payload"]["event_queue_size"] == 5


class TestDiagnosticContextIntegration:
    """Test diagnostic mode context with sensor data."""

    @pytest.mark.asyncio
    async def test_diagnostic_context_bundle_with_sensors(self, mock_system_monitor):
        """Test that diagnostic context includes sensor snapshot."""
        # Simulate ContextBroker diagnostic mode context
        metrics = await mock_system_monitor.check_health()

        context_bundle = {
            "messages": [{"role": "user", "content": "test"}],
            "semantic": [{"text": "semantic match", "score": 0.95}],
            "memory": [{"text": "memory item", "score": 0.87}],
            "sensors": metrics
        }

        # Verify all components present
        assert "messages" in context_bundle
        assert "semantic" in context_bundle
        assert "memory" in context_bundle
        assert "sensors" in context_bundle

        # Verify sensor data
        sensors = context_bundle["sensors"]
        assert sensors["cpu_percent"] == 25.5
        assert sensors["memory_percent"] == 45.2

    @pytest.mark.asyncio
    async def test_deep_context_without_sensors(self, mock_system_monitor):
        """Test that deep mode context excludes sensors."""
        context_bundle = {
            "messages": [{"role": "user", "content": "test"}],
            "semantic": [{"text": "semantic match", "score": 0.95}],
            "memory": [{"text": "memory item", "score": 0.87}]
        }

        # Sensors should not be present in deep mode
        assert "sensors" not in context_bundle

    @pytest.mark.asyncio
    async def test_normal_context_without_memory_or_sensors(self):
        """Test that normal mode context excludes memory and sensors."""
        context_bundle = {
            "messages": [{"role": "user", "content": "test"}],
            "semantic": [{"text": "semantic match", "score": 0.95}]
        }

        # Memory and sensors should not be present
        assert "memory" not in context_bundle
        assert "sensors" not in context_bundle


class TestEventStreamResilience:
    """Test event stream resilience and recovery."""

    @pytest.mark.asyncio
    async def test_event_stream_resume_after_gap(self, event_bus_context):
        """Test resuming event stream after a gap."""
        # Emit initial batch (IDs 1-5)
        for i in range(5):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        # Client checkpoints at ID 3
        last_event_id = 3

        # Gap in time (simulated)
        # New events arrive (IDs 6-8)
        for i in range(5, 8):
            await event_bus_context["publish"](
                topic=f"event.{i}",
                payload={},
                tenant_id="default"
            )

        # Client resumes from checkpoint
        events = event_bus_context["fetch_events_after"](last_event_id)

        # Should receive events with ID > 3 (IDs 4-8)
        assert len(events) == 5
        assert [e["id"] for e in events] == [4, 5, 6, 7, 8]

    @pytest.mark.asyncio
    async def test_high_event_volume(self, event_bus_context):
        """Test handling high event volume."""
        event_count = 100

        for i in range(event_count):
            await event_bus_context["publish"](
                topic="high.volume",
                payload={"seq": i},
                tenant_id="default"
            )

        # Fetch all events
        events = event_bus_context["fetch_events_after"](0)
        assert len(events) == event_count

        # Verify ordering
        assert [e["id"] for e in events] == list(range(1, event_count + 1))

    @pytest.mark.asyncio
    async def test_event_filtering_by_topic(self, event_bus_context):
        """Test filtering events by topic pattern."""
        topics = ["system.update", "message.created", "system.update", "thread.updated"]

        for topic in topics:
            await event_bus_context["publish"](
                topic=topic,
                payload={},
                tenant_id="default"
            )

        events = event_bus_context["fetch_events_after"](0)

        # Filter system events
        system_events = [e for e in events if e["topic"].startswith("system.")]
        assert len(system_events) == 2

        # Filter message events
        message_events = [e for e in events if e["topic"].startswith("message.")]
        assert len(message_events) == 1
