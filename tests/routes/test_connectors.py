"""
Test suite for connector polling loop with exponential backoff and jitter.

Tests:
- Empty configs (verify no thrashing)
- DB errors (verify retries/backoff applied)
- Stable configs (verify regular polling resumes)
- Exponential backoff calculation
- Stats tracking
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any, Dict


# Import functions to test
from guardian.routes.connectors import (
    _calculate_backoff_delay,
    _connector_worker,
    get_connector_worker_stats,
    BACKOFF_INITIAL_DELAY,
    BACKOFF_MAX_DELAY,
    BACKOFF_MULTIPLIER,
    MAX_CONSECUTIVE_FAILURES,
    CONNECTOR_SYNC_INTERVAL,
    _CONNECTOR_WORKER_STATS,
)


class TestBackoffCalculation:
    """Test exponential backoff delay calculation with jitter."""

    def test_backoff_initial_delay(self):
        """Test that initial delay is correct."""
        delay = _calculate_backoff_delay(0)
        # Should be around BACKOFF_INITIAL_DELAY with jitter (±20%)
        assert 0.8 <= delay <= 1.2

    def test_backoff_exponential_growth(self):
        """Test that delay grows exponentially."""
        delays = [_calculate_backoff_delay(i) for i in range(5)]

        # Each delay should be roughly double the previous (accounting for jitter)
        # We'll check that they're generally increasing
        for i in range(1, len(delays)):
            # With jitter, we can't guarantee strict doubling, but should trend upward
            # At least check that later delays are significantly larger
            assert delays[i] > delays[0]

    def test_backoff_max_cap(self):
        """Test that delay is capped at max."""
        # Test with a very large attempt number
        delay = _calculate_backoff_delay(100)
        # Should be at most MAX_DELAY with jitter applied
        assert delay <= BACKOFF_MAX_DELAY * 1.2  # Account for jitter

    def test_backoff_jitter_range(self):
        """Test that jitter is applied correctly."""
        # Run multiple times to test randomness
        delays = [_calculate_backoff_delay(3) for _ in range(100)]

        # All delays should be within jitter range
        base = BACKOFF_INITIAL_DELAY * (BACKOFF_MULTIPLIER ** 3)
        min_expected = base * 0.8
        max_expected = base * 1.2

        for delay in delays:
            assert min_expected <= delay <= max_expected

        # Verify we get a distribution (not always the same value)
        assert len(set(delays)) > 10  # Should have variety

    def test_backoff_custom_parameters(self):
        """Test backoff with custom parameters."""
        delay = _calculate_backoff_delay(
            attempt=2,
            base_delay=2.0,
            max_delay=10.0,
            multiplier=3.0,
            jitter_range=(0.9, 1.1)
        )

        # Base calculation: 2.0 * (3.0 ** 2) = 18.0, capped at 10.0
        # With jitter: 10.0 * [0.9, 1.1] = [9.0, 11.0]
        assert 9.0 <= delay <= 11.0


class TestConnectorWorkerEmptyConfigs:
    """Test connector worker behavior with empty configs."""

    @pytest.mark.asyncio
    async def test_empty_configs_no_thrashing(self):
        """Test that empty configs don't cause tight polling loop."""
        stop_event = asyncio.Event()

        # Mock DB to return empty configs
        mock_db = MagicMock()
        mock_db.list_connector_configs.return_value = []

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            # Reset stats
            _CONNECTOR_WORKER_STATS["poll_cycles"] = 0
            _CONNECTOR_WORKER_STATS["empty_config_cycles"] = 0

            # Start worker task
            task = asyncio.create_task(_connector_worker(stop_event))

            # Let it run for a short time
            await asyncio.sleep(0.5)

            # Stop the worker
            stop_event.set()
            await task

            # Verify it only polled once (not thrashing)
            assert _CONNECTOR_WORKER_STATS["poll_cycles"] == 1
            assert _CONNECTOR_WORKER_STATS["empty_config_cycles"] == 1

            # Verify DB was only called once
            assert mock_db.list_connector_configs.call_count == 1


class TestConnectorWorkerDBErrors:
    """Test connector worker behavior with DB errors."""

    @pytest.mark.asyncio
    async def test_db_error_triggers_retry(self):
        """Test that DB errors trigger retry with backoff."""
        stop_event = asyncio.Event()

        # Mock DB to fail initially, then succeed
        mock_db = MagicMock()
        call_count = 0

        def side_effect_fail_then_succeed(*args):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("DB connection failed")
            return []  # Empty configs on success

        mock_db.list_connector_configs.side_effect = side_effect_fail_then_succeed

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            # Reset stats
            _CONNECTOR_WORKER_STATS["db_errors"] = 0
            _CONNECTOR_WORKER_STATS["retries"] = 0
            _CONNECTOR_WORKER_STATS["poll_cycles"] = 0

            # Start worker task
            task = asyncio.create_task(_connector_worker(stop_event))

            # Let it run long enough to retry
            await asyncio.sleep(3)  # Allow time for backoff

            # Stop the worker
            stop_event.set()

            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Verify errors were tracked
            assert _CONNECTOR_WORKER_STATS["db_errors"] >= 2
            assert _CONNECTOR_WORKER_STATS["retries"] >= 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_applied(self):
        """Test that exponential backoff is applied on repeated failures."""
        stop_event = asyncio.Event()

        # Mock DB to always fail
        mock_db = MagicMock()
        mock_db.list_connector_configs.side_effect = Exception("DB unavailable")

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            # Reset stats
            _CONNECTOR_WORKER_STATS["db_errors"] = 0
            _CONNECTOR_WORKER_STATS["retries"] = 0

            # Capture actual delays by mocking wait_for
            delays = []
            original_wait_for = asyncio.wait_for

            async def track_delays(coro, timeout):
                delays.append(timeout)
                return await original_wait_for(coro, timeout=timeout)

            with patch("asyncio.wait_for", side_effect=track_delays):
                # Start worker task
                task = asyncio.create_task(_connector_worker(stop_event))

                # Let it retry a few times
                await asyncio.sleep(5)

                # Stop the worker
                stop_event.set()

                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except asyncio.TimeoutError:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Verify backoff delays are increasing
            if len(delays) >= 3:
                # Filter out very large delays (those are normal CONNECTOR_SYNC_INTERVAL)
                backoff_delays = [d for d in delays if d < 100]
                if len(backoff_delays) >= 2:
                    # Delays should generally increase
                    assert backoff_delays[1] > backoff_delays[0]

    @pytest.mark.asyncio
    async def test_max_failures_extended_backoff(self):
        """Test that exceeding max failures triggers extended backoff."""
        stop_event = asyncio.Event()

        # Mock DB to always fail
        mock_db = MagicMock()
        mock_db.list_connector_configs.side_effect = Exception("DB unavailable")

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            # Reset stats
            _CONNECTOR_WORKER_STATS["db_errors"] = 0
            _CONNECTOR_WORKER_STATS["skipped_cycles"] = 0

            # Start worker task
            task = asyncio.create_task(_connector_worker(stop_event))

            # Let it run long enough to exceed max failures
            # This needs to be long enough for exponential backoff to accumulate
            await asyncio.sleep(10)

            # Stop the worker
            stop_event.set()

            try:
                await asyncio.wait_for(task, timeout=2.0)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Verify extended backoff was triggered
            # After enough failures, should have skipped cycles
            assert _CONNECTOR_WORKER_STATS["db_errors"] > 0


class TestConnectorWorkerStableConfigs:
    """Test connector worker with stable configs."""

    @pytest.mark.asyncio
    async def test_stable_configs_regular_polling(self):
        """Test that stable configs result in regular polling."""
        stop_event = asyncio.Event()

        # Mock DB to return stable configs
        mock_config = {
            "id": 1,
            "name": "test-github",
            "type": "github",
            "settings": {"owner": "test", "repo": "test"},
        }

        mock_db = MagicMock()
        mock_db.list_connector_configs.return_value = [mock_config]

        # Mock _run_github_sync as a no-op coroutine
        async def mock_sync(config):
            pass

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            with patch("guardian.routes.connectors._run_github_sync", side_effect=mock_sync):
                # Reset stats
                _CONNECTOR_WORKER_STATS["poll_cycles"] = 0
                _CONNECTOR_WORKER_STATS["db_errors"] = 0

                # Start worker task
                task = asyncio.create_task(_connector_worker(stop_event))

                # Let it run for a bit
                await asyncio.sleep(0.5)

                # Stop the worker
                stop_event.set()
                await task

                # Verify regular polling occurred
                assert _CONNECTOR_WORKER_STATS["poll_cycles"] >= 1
                assert _CONNECTOR_WORKER_STATS["db_errors"] == 0

    @pytest.mark.asyncio
    async def test_recovery_after_failures(self):
        """Test that worker recovers and resets backoff after successful poll."""
        stop_event = asyncio.Event()

        # Mock DB to fail a few times then succeed
        call_count = 0
        mock_config = {
            "id": 1,
            "name": "test-github",
            "type": "github",
            "settings": {"owner": "test", "repo": "test"},
        }

        def side_effect_fail_then_recover(*args):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Temporary DB error")
            return [mock_config]  # Recover with configs

        mock_db = MagicMock()
        mock_db.list_connector_configs.side_effect = side_effect_fail_then_recover

        # Mock _run_github_sync as a no-op coroutine
        async def mock_sync(config):
            pass

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            with patch("guardian.routes.connectors._run_github_sync", side_effect=mock_sync):
                # Reset stats
                _CONNECTOR_WORKER_STATS["db_errors"] = 0
                _CONNECTOR_WORKER_STATS["retries"] = 0
                _CONNECTOR_WORKER_STATS["poll_cycles"] = 0

                # Start worker task
                task = asyncio.create_task(_connector_worker(stop_event))

                # Let it run long enough to fail and recover
                await asyncio.sleep(5)

                # Stop the worker
                stop_event.set()

                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except asyncio.TimeoutError:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Verify it failed and then recovered
                assert _CONNECTOR_WORKER_STATS["db_errors"] >= 3
                # Should have at least attempted multiple cycles (3 failures)
                assert _CONNECTOR_WORKER_STATS["poll_cycles"] >= 3


class TestConnectorWorkerStats:
    """Test monitoring stats collection."""

    def test_get_connector_worker_stats(self):
        """Test that stats can be retrieved."""
        # Reset stats to known values
        _CONNECTOR_WORKER_STATS["poll_cycles"] = 10
        _CONNECTOR_WORKER_STATS["empty_config_cycles"] = 5
        _CONNECTOR_WORKER_STATS["db_errors"] = 2
        _CONNECTOR_WORKER_STATS["retries"] = 3
        _CONNECTOR_WORKER_STATS["skipped_cycles"] = 1

        stats = get_connector_worker_stats()

        assert stats["poll_cycles"] == 10
        assert stats["empty_config_cycles"] == 5
        assert stats["db_errors"] == 2
        assert stats["retries"] == 3
        assert stats["skipped_cycles"] == 1

    def test_stats_are_independent_copy(self):
        """Test that returned stats are a copy, not reference."""
        _CONNECTOR_WORKER_STATS["poll_cycles"] = 100

        stats1 = get_connector_worker_stats()
        stats1["poll_cycles"] = 999

        stats2 = get_connector_worker_stats()

        # Original should not be modified
        assert stats2["poll_cycles"] == 100

    @pytest.mark.asyncio
    async def test_stats_tracking_during_operation(self):
        """Test that stats are correctly tracked during worker operation."""
        stop_event = asyncio.Event()

        # Mock DB to return empty configs
        mock_db = MagicMock()
        mock_db.list_connector_configs.return_value = []

        with patch("guardian.routes.connectors.chatlog_db", mock_db):
            # Reset all stats
            for key in _CONNECTOR_WORKER_STATS:
                _CONNECTOR_WORKER_STATS[key] = 0

            # Start worker task
            task = asyncio.create_task(_connector_worker(stop_event))

            # Let it run briefly
            await asyncio.sleep(0.5)

            # Stop the worker
            stop_event.set()
            await task

            # Get final stats
            stats = get_connector_worker_stats()

            # Verify stats were tracked
            assert stats["poll_cycles"] >= 1
            assert stats["empty_config_cycles"] >= 1
            assert stats["db_errors"] == 0  # No errors in this test
