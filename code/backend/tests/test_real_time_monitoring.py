"""
Unit tests for the real-time risk monitoring module.

This module contains tests for the real-time risk monitoring functionality.
"""

import time
import unittest
from datetime import datetime

from risk.aggregation.real_time_monitoring import (
    AlertChannel,
    AlertSeverity,
    RiskAlert,
    RiskMonitor,
)


class TestRiskAlert(unittest.TestCase):
    """Test cases for the RiskAlert class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.alert = RiskAlert(
            alert_id="ALERT001",
            metric_name="portfolio_var",
            severity=AlertSeverity.WARNING,
            message="Portfolio VaR exceeded warning threshold",
            timestamp=datetime.now(),
            value=12.5,
            threshold=10.0,
            channels=[AlertChannel.DASHBOARD, AlertChannel.EMAIL],
        )

    def test_alert_properties(self) -> Any:
        """Test that alert properties are correctly set."""
        self.assertEqual(self.alert.alert_id, "ALERT001")
        self.assertEqual(self.alert.metric_name, "portfolio_var")
        self.assertEqual(self.alert.severity, AlertSeverity.WARNING)
        self.assertEqual(self.alert.message, "Portfolio VaR exceeded warning threshold")
        self.assertEqual(self.alert.value, 12.5)
        self.assertEqual(self.alert.threshold, 10.0)
        self.assertEqual(len(self.alert.channels), 2)
        self.assertIn(AlertChannel.DASHBOARD, self.alert.channels)
        self.assertIn(AlertChannel.EMAIL, self.alert.channels)
        self.assertFalse(self.alert.acknowledged)
        self.assertIsNone(self.alert.acknowledged_by)
        self.assertIsNone(self.alert.acknowledged_at)


class TestRiskMonitor(unittest.TestCase):
    """Test cases for the RiskMonitor class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.monitor = RiskMonitor(update_interval=1)

        def calc_var():
            return 15.0

        self.monitor.register_metric(
            metric_id="portfolio_var",
            name="Portfolio VaR",
            calculation_func=calc_var,
            description="Value at Risk for the entire portfolio",
        )

    def test_register_metric(self) -> Any:
        """Test registering a risk metric."""
        self.assertIn("portfolio_var", self.monitor.metrics)
        self.assertEqual(self.monitor.metrics["portfolio_var"]["name"], "Portfolio VaR")
        self.assertEqual(
            self.monitor.metrics["portfolio_var"]["description"],
            "Value at Risk for the entire portfolio",
        )

    def test_set_threshold(self) -> Any:
        """Test setting alert thresholds for a risk metric."""
        self.monitor.set_threshold(
            metric_id="portfolio_var",
            warning_level=10.0,
            critical_level=15.0,
            emergency_level=20.0,
            channels=[AlertChannel.DASHBOARD, AlertChannel.EMAIL],
        )
        self.assertIn("portfolio_var", self.monitor.thresholds)
        self.assertEqual(self.monitor.thresholds["portfolio_var"]["warning"], 10.0)
        self.assertEqual(self.monitor.thresholds["portfolio_var"]["critical"], 15.0)
        self.assertEqual(self.monitor.thresholds["portfolio_var"]["emergency"], 20.0)
        self.assertEqual(len(self.monitor.thresholds["portfolio_var"]["channels"]), 2)

    def test_update_metric(self) -> Any:
        """Test updating a risk metric."""
        value = self.monitor.update_metric("portfolio_var")
        self.assertEqual(value, 15.0)
        self.assertEqual(self.monitor.metrics["portfolio_var"]["last_value"], 15.0)
        self.assertIsNotNone(self.monitor.metrics["portfolio_var"]["last_updated"])
        self.assertEqual(len(self.monitor.metrics["portfolio_var"]["history"]), 1)

    def test_update_metric_nonexistent(self) -> Any:
        """Test updating a non-existent metric."""
        with self.assertRaises(KeyError):
            self.monitor.update_metric("nonexistent_metric")

    def test_threshold_alert_generation(self) -> Any:
        """Test that alerts are generated when thresholds are exceeded."""
        self.monitor.set_threshold(
            metric_id="portfolio_var",
            warning_level=10.0,
            critical_level=15.0,
            emergency_level=20.0,
        )
        self.monitor.update_metric("portfolio_var")
        self.assertEqual(len(self.monitor.alerts), 1)
        self.assertEqual(self.monitor.alerts[0].severity, AlertSeverity.CRITICAL)

    def test_acknowledge_alert(self) -> Any:
        """Test acknowledging an alert."""
        self.monitor.set_threshold(
            metric_id="portfolio_var", warning_level=10.0, critical_level=15.0
        )
        self.monitor.update_metric("portfolio_var")
        alert_id = self.monitor.alerts[0].alert_id
        result = self.monitor.acknowledge_alert(alert_id, "test_user")
        self.assertTrue(result)
        self.assertTrue(self.monitor.alerts[0].acknowledged)
        self.assertEqual(self.monitor.alerts[0].acknowledged_by, "test_user")
        self.assertIsNotNone(self.monitor.alerts[0].acknowledged_at)

    def test_acknowledge_nonexistent_alert(self) -> Any:
        """Test acknowledging a non-existent alert."""
        result = self.monitor.acknowledge_alert("nonexistent_alert", "test_user")
        self.assertFalse(result)

    def test_get_metric_history(self) -> Any:
        """Test getting historical values for a metric."""
        for _ in range(3):
            self.monitor.update_metric("portfolio_var")
            time.sleep(0.1)
        history = self.monitor.get_metric_history("portfolio_var")
        self.assertEqual(len(history), 3)
        for timestamp, value in history:
            self.assertIsInstance(timestamp, datetime)
            self.assertEqual(value, 15.0)

    def test_get_metric_history_with_time_range(self) -> Any:
        """Test getting historical values for a metric with time range filtering."""
        for _ in range(3):
            self.monitor.update_metric("portfolio_var")
            time.sleep(0.1)
        middle_time = self.monitor.metrics["portfolio_var"]["history"][1][0]
        history = self.monitor.get_metric_history(
            "portfolio_var", start_time=middle_time
        )
        self.assertEqual(len(history), 2)
        history = self.monitor.get_metric_history("portfolio_var", end_time=middle_time)
        self.assertEqual(len(history), 2)

    def test_get_active_alerts(self) -> Any:
        """Test getting active (unacknowledged) alerts."""
        self.monitor.set_threshold(
            metric_id="portfolio_var",
            warning_level=10.0,
            critical_level=15.0,
            emergency_level=20.0,
        )

        def calc_es():
            return 25.0

        self.monitor.register_metric(
            metric_id="expected_shortfall",
            name="Expected Shortfall",
            calculation_func=calc_es,
        )
        self.monitor.set_threshold(
            metric_id="expected_shortfall",
            warning_level=20.0,
            critical_level=25.0,
            emergency_level=30.0,
        )
        self.monitor.update_metric("portfolio_var")
        self.monitor.update_metric("expected_shortfall")
        self.monitor.acknowledge_alert(self.monitor.alerts[0].alert_id, "test_user")
        active_alerts = self.monitor.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(active_alerts[0].metric_name, "Expected Shortfall")

    def test_generate_risk_dashboard_data(self) -> Any:
        """Test generating data for a risk dashboard."""
        self.monitor.set_threshold(
            metric_id="portfolio_var",
            warning_level=10.0,
            critical_level=15.0,
            emergency_level=20.0,
        )
        self.monitor.update_metric("portfolio_var")
        dashboard_data = self.monitor.generate_risk_dashboard_data()
        self.assertIn("timestamp", dashboard_data)
        self.assertIn("metrics", dashboard_data)
        self.assertIn("active_alerts", dashboard_data)
        self.assertIn("alerts_by_severity", dashboard_data)
        self.assertIn("recent_alerts", dashboard_data)
        self.assertIn("portfolio_var", dashboard_data["metrics"])
        self.assertEqual(
            dashboard_data["metrics"]["portfolio_var"]["current_value"], 15.0
        )
        self.assertIn("thresholds", dashboard_data["metrics"]["portfolio_var"])
        self.assertEqual(dashboard_data["active_alerts"], 1)
        self.assertEqual(dashboard_data["alerts_by_severity"]["critical"], 1)
        self.assertEqual(len(dashboard_data["recent_alerts"]), 1)

    def test_monitoring_thread(self) -> Any:
        """Test the monitoring thread functionality."""
        update_count = [0]

        def counter_metric():
            update_count[0] += 1
            return update_count[0]

        self.monitor.register_metric(
            metric_id="counter", name="Counter Metric", calculation_func=counter_metric
        )
        self.monitor.start_monitoring()
        time.sleep(2.5)
        self.monitor.stop_monitoring()
        self.assertGreater(update_count[0], 1)
        self.assertGreater(len(self.monitor.metrics["counter"]["history"]), 1)


if __name__ == "__main__":
    unittest.main()
