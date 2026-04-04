"""
Tests for the market connectivity module.

This module contains tests for the market connectivity functionality,
including reconnection logic, failure simulation, and data feed stability.
"""

import datetime
import os
import sys
import unittest
from typing import Any
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import execution_engine.order_management.market_connectivity_base as _base_module
from execution_engine.order_management.market_connectivity import (
    ConnectionStatus,
    FailureMode,
    MarketConnectivityManager,
    VenueAdapter,
    VenueConfig,
)


class TestVenueAdapter(unittest.TestCase):
    """Test cases for the VenueAdapter class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""

        self.config = VenueConfig(
            venue_id="test_venue",
            name="Test Exchange",
            host="test.exchange.com",
            port=443,
            enabled=True,
        )
        self.adapter = VenueAdapter(self.config)
        self.adapter._connect_impl = MagicMock(return_value=True)

        self._orig_base_submit = _base_module.VenueAdapter.submit_order
        _base_module.VenueAdapter.submit_order = lambda self, od: (
            True,
            "test_order_id",
            {},
        )

    def tearDown(self) -> Any:
        """Restore patched base methods."""
        _base_module.VenueAdapter.submit_order = self._orig_base_submit
        self.adapter.disconnect()

    def test_initialization(self) -> Any:
        self.assertEqual(self.adapter.config.venue_id, "test_venue")
        self.assertEqual(self.adapter.status, ConnectionStatus.DISCONNECTED)
        self.assertFalse(self.adapter.failure_simulation_enabled)
        self.assertEqual(self.adapter.messages_sent, 0)
        self.assertEqual(self.adapter.messages_received, 0)

    def test_connect_disconnect(self) -> Any:
        success = self.adapter.connect()
        self.assertTrue(success)
        self.assertEqual(self.adapter.status, ConnectionStatus.CONNECTED)
        self.adapter._connect_impl.assert_called_once()

        success = self.adapter.disconnect()
        self.assertTrue(success)
        self.assertEqual(self.adapter.status, ConnectionStatus.DISCONNECTED)

    def test_connection_failure(self) -> Any:
        self.adapter._connect_impl.return_value = False
        success = self.adapter.connect()
        self.assertFalse(success)
        self.assertEqual(self.adapter.status, ConnectionStatus.ERROR)
        self.assertEqual(self.adapter.connection_failures, 1)

    def test_failure_simulation_disconnect(self) -> Any:
        self.adapter.enable_failure_simulation(True)
        self.adapter.configure_failure_mode(FailureMode.DISCONNECT, 1.0)
        success = self.adapter.connect()
        self.assertFalse(success)
        self.assertEqual(self.adapter.status, ConnectionStatus.ERROR)
        self.assertEqual(self.adapter.last_error, "Simulated connection failure")

    def test_health_check(self) -> Any:
        self.adapter.connect()
        self.assertEqual(self.adapter.status, ConnectionStatus.CONNECTED)
        is_healthy = self.adapter._check_connection_health()
        self.assertTrue(is_healthy)
        self.adapter.last_activity_time = datetime.datetime.now() - datetime.timedelta(
            seconds=120
        )
        is_healthy = self.adapter._check_connection_health()
        self.assertFalse(is_healthy)

    def test_failure_simulation_timeout(self) -> Any:
        self.adapter.connect()
        self.assertEqual(self.adapter.status, ConnectionStatus.CONNECTED)
        self.adapter.enable_failure_simulation(True)
        self.adapter.configure_failure_mode(FailureMode.TIMEOUT, 1.0)
        is_healthy = self.adapter._check_connection_health()
        self.assertFalse(is_healthy)

    def test_order_submission_with_failure_simulation(self) -> Any:
        self.adapter.connect()
        self.assertEqual(self.adapter.status, ConnectionStatus.CONNECTED)
        order_data = {"symbol": "AAPL", "quantity": 100, "price": 150.0}

        success, order_id, response = self.adapter.submit_order(order_data)
        self.assertTrue(success)
        self.assertNotEqual(order_id, "")

        self.adapter.enable_failure_simulation(True)
        self.adapter.configure_failure_mode(FailureMode.TIMEOUT, 1.0)
        success, order_id, response = self.adapter.submit_order(order_data)
        self.assertFalse(success)
        self.assertEqual(order_id, "")
        self.assertEqual(response["error"], "Simulated timeout")

    def test_market_data_processing_with_failure_simulation(self) -> Any:
        self.adapter.connect()
        self.assertEqual(self.adapter.status, ConnectionStatus.CONNECTED)
        data = {
            "venue_id": "test_venue",
            "instrument_id": "AAPL",
            "timestamp": datetime.datetime.now(),
            "bid": 150.0,
            "ask": 150.1,
            "last": 150.05,
            "volume": 1000,
        }
        update = self.adapter.process_market_data(data)
        self.assertIsNotNone(update)

        self.adapter.enable_failure_simulation(True)
        self.adapter.configure_failure_mode(FailureMode.DATA_CORRUPTION, 1.0)
        update = self.adapter.process_market_data(data)
        self.assertIsNone(update)

        self.adapter.configure_failure_mode(FailureMode.DATA_CORRUPTION, 0.0)
        self.adapter.configure_failure_mode(FailureMode.PARTIAL_DATA, 1.0)
        update = self.adapter.process_market_data(data)
        self.assertIsNotNone(update)
        self.assertIsNone(update.bid)
        self.assertIsNone(update.ask)

    def test_get_status(self) -> Any:
        self.adapter.connect()
        status = self.adapter.get_status()
        self.assertEqual(status["venue_id"], "test_venue")
        self.assertEqual(status["status"], "connected")
        self.assertIn("messages_sent", status)
        self.assertIn("messages_received", status)
        self.assertIn("connection_attempts", status)
        self.assertIn("failure_simulation_enabled", status)


class TestMarketConnectivityManager(unittest.TestCase):
    """Test cases for the MarketConnectivityManager class."""

    def setUp(self) -> Any:
        self.manager = MarketConnectivityManager()
        self.venue1_config = VenueConfig(
            venue_id="venue1",
            name="Exchange 1",
            host="exchange1.com",
            port=443,
            enabled=True,
        )
        self.venue2_config = VenueConfig(
            venue_id="venue2",
            name="Exchange 2",
            host="exchange2.com",
            port=443,
            enabled=True,
        )
        self.manager.add_venue(self.venue1_config)
        self.manager.add_venue(self.venue2_config)
        self.manager.venues["venue1"]._connect_impl = MagicMock(return_value=True)
        self.manager.venues["venue2"]._connect_impl = MagicMock(return_value=True)

    def tearDown(self) -> Any:
        self.manager.disconnect_all()

    def test_initialization(self) -> Any:
        self.assertEqual(len(self.manager.venues), 2)
        self.assertFalse(self.manager.global_failure_simulation_enabled)

    def test_connect_all_venues(self) -> Any:
        results = self.manager.connect_all()
        self.assertTrue(results["venue1"])
        self.assertTrue(results["venue2"])
        self.assertEqual(
            self.manager.venues["venue1"].status, ConnectionStatus.CONNECTED
        )
        self.assertEqual(
            self.manager.venues["venue2"].status, ConnectionStatus.CONNECTED
        )

    def test_global_failure_simulation(self) -> Any:
        self.manager.enable_global_failure_simulation(True)
        self.assertTrue(self.manager.global_failure_simulation_enabled)
        self.assertTrue(self.manager.venues["venue1"].failure_simulation_enabled)
        self.assertTrue(self.manager.venues["venue2"].failure_simulation_enabled)

        self.manager.enable_global_failure_simulation(False)
        self.assertFalse(self.manager.global_failure_simulation_enabled)
        self.assertFalse(self.manager.venues["venue1"].failure_simulation_enabled)
        self.assertFalse(self.manager.venues["venue2"].failure_simulation_enabled)

    def test_venue_specific_failure_configuration(self) -> Any:
        success = self.manager.configure_venue_failure(
            venue_id="venue1", mode=FailureMode.DISCONNECT, probability=0.5
        )
        self.assertTrue(success)
        self.assertEqual(
            self.manager.venues["venue1"].failure_probabilities[FailureMode.DISCONNECT],
            0.5,
        )
        self.assertNotIn(
            FailureMode.DISCONNECT, self.manager.venues["venue2"].failure_probabilities
        )

    def test_simulate_venue_failure(self) -> Any:
        self.manager.connect_all()
        self.manager.venues["venue1"].reconnection_manager.connection_lost = (
            lambda: None
        )
        success = self.manager.simulate_venue_failure("venue1")
        self.assertTrue(success)
        self.assertEqual(self.manager.venues["venue1"].status, ConnectionStatus.ERROR)

    def test_simulate_market_data_issue(self) -> Any:
        self.manager.connect_all()
        success = self.manager.simulate_market_data_issue(
            venue_id="venue1", issue_type=FailureMode.DATA_CORRUPTION
        )
        self.assertTrue(success)
        self.assertTrue(self.manager.venues["venue1"].failure_simulation_enabled)
        self.assertEqual(
            self.manager.venues["venue1"].failure_probabilities[
                FailureMode.DATA_CORRUPTION
            ],
            1.0,
        )

    def test_get_connection_health_report(self) -> Any:
        self.manager.connect_all()
        report = self.manager.get_connection_health_report()
        self.assertEqual(report["total_venues"], 2)
        self.assertEqual(report["connected_venues"], 2)
        self.assertEqual(report["overall_status"], "healthy")

        self.manager.venues["venue1"].reconnection_manager.connection_lost = (
            lambda: None
        )
        self.manager.venues["venue1"].status = ConnectionStatus.ERROR
        self.manager.venues["venue1"].last_error = "Simulated complete failure"
        report = self.manager.get_connection_health_report()
        self.assertEqual(report["connected_venues"], 1)
        self.assertEqual(report["overall_status"], "degraded")

    def test_reset_failure_simulations(self) -> Any:
        self.manager.enable_global_failure_simulation(True)
        self.manager.configure_venue_failure(
            venue_id="venue1", mode=FailureMode.DISCONNECT, probability=0.5
        )
        self.manager.reset_failure_simulations()
        self.assertFalse(self.manager.global_failure_simulation_enabled)
        self.assertFalse(self.manager.venues["venue1"].failure_simulation_enabled)
        self.assertFalse(self.manager.venues["venue2"].failure_simulation_enabled)


if __name__ == "__main__":
    unittest.main()
