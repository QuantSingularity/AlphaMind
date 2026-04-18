import time
import unittest
from unittest.mock import MagicMock

from execution.order_management.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
    ReconnectionState,
)


class TestReconnectionManager(unittest.TestCase):
    """Test cases for the ReconnectionManager class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.config = ReconnectionConfig(
            initial_delay=0.1,
            max_delay=0.5,
            backoff_factor=2.0,
            jitter=0.1,
            max_attempts=5,
            circuit_break_threshold=3,
            circuit_break_timeout=0.5,
            health_check_interval=0.2,
        )
        self.reconnection_manager = ReconnectionManager(self.config)
        self.connect_callback = MagicMock(return_value=True)
        self.health_check_callback = MagicMock(return_value=True)
        self.on_reconnect_callback = MagicMock()
        self.on_give_up_callback = MagicMock()

    def test_initialization(self) -> Any:
        """Test initialization of reconnection manager."""
        self.assertEqual(self.reconnection_manager.state, ReconnectionState.IDLE)
        self.assertEqual(self.reconnection_manager.stats.total_attempts, 0)
        self.assertEqual(self.reconnection_manager.stats.successful_reconnects, 0)
        self.assertEqual(self.reconnection_manager.stats.failed_attempts, 0)
        self.assertFalse(self.reconnection_manager.is_running)

    def test_start_stop(self) -> Any:
        """Test starting and stopping the reconnection manager."""
        self.reconnection_manager.start(
            connection_id="test_connection",
            connect_callback=self.connect_callback,
            health_check_callback=self.health_check_callback,
            on_reconnect_callback=self.on_reconnect_callback,
            on_give_up_callback=self.on_give_up_callback,
        )
        self.assertTrue(self.reconnection_manager.is_running)
        self.assertEqual(self.reconnection_manager.connection_id, "test_connection")
        self.reconnection_manager.stop()
        self.assertFalse(self.reconnection_manager.is_running)

    def test_successful_reconnection(self) -> Any:
        """Test successful reconnection attempt."""
        self.reconnection_manager.start(
            connection_id="test_connection",
            connect_callback=self.connect_callback,
            on_reconnect_callback=self.on_reconnect_callback,
        )
        self.reconnection_manager.connection_lost()
        time.sleep(0.2)
        self.connect_callback.assert_called_once()
        self.on_reconnect_callback.assert_called_once_with(True)
        self.assertEqual(self.reconnection_manager.stats.total_attempts, 1)
        self.assertEqual(self.reconnection_manager.stats.successful_reconnects, 1)
        self.assertEqual(self.reconnection_manager.stats.failed_attempts, 0)

    def test_failed_reconnection_with_backoff(self) -> Any:
        """Test failed reconnection attempt with backoff."""
        self.connect_callback.return_value = False
        config = ReconnectionConfig(
            initial_delay=0.1,
            max_delay=0.5,
            backoff_factor=2.0,
            jitter=0.0,
            max_attempts=3,
            circuit_break_threshold=5,
        )
        reconnection_manager = ReconnectionManager(config)
        reconnection_manager.start(
            connection_id="test_connection",
            connect_callback=self.connect_callback,
            on_reconnect_callback=self.on_reconnect_callback,
        )
        reconnection_manager.connection_lost()
        time.sleep(0.25)
        self.assertEqual(self.connect_callback.call_count, 2)
        self.assertEqual(self.on_reconnect_callback.call_count, 2)
        self.on_reconnect_callback.assert_called_with(False)
        self.assertEqual(reconnection_manager.stats.total_attempts, 2)
        self.assertEqual(reconnection_manager.stats.successful_reconnects, 0)
        self.assertEqual(reconnection_manager.stats.failed_attempts, 2)
        self.assertEqual(reconnection_manager.stats.consecutive_failures, 2)

    def test_circuit_breaker_activation(self) -> Any:
        """Test circuit breaker activation after consecutive failures."""
        self.connect_callback.return_value = False
        self.reconnection_manager.start(
            connection_id="test_connection", connect_callback=self.connect_callback
        )
        self.reconnection_manager.connection_lost()
        time.sleep(0.5)
        self.assertEqual(
            self.reconnection_manager.state, ReconnectionState.CIRCUIT_OPEN
        )
        self.assertEqual(self.connect_callback.call_count, 3)
        time.sleep(0.6)
        self.connect_callback.reset_mock()
        self.reconnection_manager.connection_lost()
        time.sleep(0.2)
        self.assertEqual(self.connect_callback.call_count, 1)

    def test_max_attempts_give_up(self) -> Any:
        """Test stopping after maximum number of attempts."""
        self.connect_callback.return_value = False
        config = ReconnectionConfig(
            initial_delay=0.1, max_delay=0.2, max_attempts=2, circuit_break_threshold=10
        )
        reconnection_manager = ReconnectionManager(config)
        reconnection_manager.start(
            connection_id="test_connection",
            connect_callback=self.connect_callback,
            on_give_up_callback=self.on_give_up_callback,
        )
        reconnection_manager.connection_lost()
        time.sleep(0.5)
        self.assertEqual(self.connect_callback.call_count, 2)
        self.on_give_up_callback.assert_called_once()

    def test_connection_established_resets_state(self) -> Any:
        """Test that connection_established resets reconnection state."""
        self.connect_callback.return_value = False
        self.reconnection_manager.start(
            connection_id="test_connection", connect_callback=self.connect_callback
        )
        self.reconnection_manager.connection_lost()
        time.sleep(0.2)
        self.assertNotEqual(self.reconnection_manager.state, ReconnectionState.IDLE)
        self.reconnection_manager.connection_established()
        self.assertEqual(self.reconnection_manager.state, ReconnectionState.IDLE)
        self.assertEqual(
            self.reconnection_manager.current_delay, self.config.initial_delay
        )
        self.assertEqual(self.reconnection_manager.stats.consecutive_failures, 0)

    def test_get_stats(self) -> Any:
        """Test getting reconnection statistics."""
        self.reconnection_manager.start(
            connection_id="test_connection", connect_callback=self.connect_callback
        )
        self.reconnection_manager.connection_lost()
        time.sleep(0.2)
        stats = self.reconnection_manager.get_stats()
        self.assertEqual(stats["connection_id"], "test_connection")
        self.assertEqual(stats["total_attempts"], 1)
        self.assertEqual(stats["successful_reconnects"], 1)
        self.assertEqual(stats["failed_attempts"], 0)


if __name__ == "__main__":
    unittest.main()
