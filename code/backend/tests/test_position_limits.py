"""
Unit tests for the position limits management module.

This module contains tests for the position limits functionality.
"""

import unittest

from risk.aggregation.position_limits import (
    LimitScope,
    LimitType,
    PositionLimit,
    PositionLimitsManager,
)


class TestPositionLimit(unittest.TestCase):
    """Test cases for the PositionLimit class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.limit = PositionLimit(
            limit_id="TEST001",
            limit_type=LimitType.NOTIONAL,
            scope=LimitScope.INSTRUMENT,
            scope_value="AAPL",
            soft_limit=1000000.0,
            hard_limit=2000000.0,
            description="Apple position limit",
        )

    def test_is_breached_no_breach(self) -> Any:
        """Test that is_breached returns False when value is below limits."""
        is_breached, severity = self.limit.is_breached(500000.0)
        self.assertFalse(is_breached)
        self.assertEqual(severity, "none")

    def test_is_breached_soft_breach(self) -> Any:
        """Test that is_breached returns True with 'soft' when value exceeds soft limit."""
        is_breached, severity = self.limit.is_breached(1500000.0)
        self.assertTrue(is_breached)
        self.assertEqual(severity, "soft")

    def test_is_breached_hard_breach(self) -> Any:
        """Test that is_breached returns True with 'hard' when value exceeds hard limit."""
        is_breached, severity = self.limit.is_breached(2500000.0)
        self.assertTrue(is_breached)
        self.assertEqual(severity, "hard")

    def test_is_breached_inactive(self) -> Any:
        """Test that is_breached returns False when limit is inactive."""
        self.limit.active = False
        is_breached, severity = self.limit.is_breached(2500000.0)
        self.assertFalse(is_breached)
        self.assertEqual(severity, "none")


class TestPositionLimitsManager(unittest.TestCase):
    """Test cases for the PositionLimitsManager class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.manager = PositionLimitsManager()
        self.limit1 = PositionLimit(
            limit_id="AAPL_NOTIONAL",
            limit_type=LimitType.NOTIONAL,
            scope=LimitScope.INSTRUMENT,
            scope_value="AAPL",
            soft_limit=1000000.0,
            hard_limit=2000000.0,
        )
        self.limit2 = PositionLimit(
            limit_id="TECH_SECTOR",
            limit_type=LimitType.PERCENTAGE,
            scope=LimitScope.SECTOR,
            scope_value="TECH",
            soft_limit=30.0,
            hard_limit=40.0,
        )

    def test_add_limit(self) -> Any:
        """Test adding a position limit."""
        self.manager.add_limit(self.limit1)
        self.assertIn("AAPL_NOTIONAL", self.manager.limits)
        self.assertEqual(self.manager.limits["AAPL_NOTIONAL"], self.limit1)

    def test_remove_limit(self) -> Any:
        """Test removing a position limit."""
        self.manager.add_limit(self.limit1)
        result = self.manager.remove_limit("AAPL_NOTIONAL")
        self.assertTrue(result)
        self.assertNotIn("AAPL_NOTIONAL", self.manager.limits)

    def test_remove_nonexistent_limit(self) -> Any:
        """Test removing a non-existent position limit."""
        result = self.manager.remove_limit("NONEXISTENT")
        self.assertFalse(result)

    def test_update_limit(self) -> Any:
        """Test updating a position limit."""
        self.manager.add_limit(self.limit1)
        result = self.manager.update_limit(
            "AAPL_NOTIONAL", soft_limit=1500000.0, hard_limit=2500000.0
        )
        self.assertTrue(result)
        self.assertEqual(self.manager.limits["AAPL_NOTIONAL"].soft_limit, 1500000.0)
        self.assertEqual(self.manager.limits["AAPL_NOTIONAL"].hard_limit, 2500000.0)

    def test_update_nonexistent_limit(self) -> Any:
        """Test updating a non-existent position limit."""
        result = self.manager.update_limit("NONEXISTENT", soft_limit=1500000.0)
        self.assertFalse(result)

    def test_check_limit(self) -> Any:
        """Test checking a specific position limit."""
        self.manager.add_limit(self.limit1)
        is_breached, severity = self.manager.check_limit("AAPL_NOTIONAL", 1500000.0)
        self.assertTrue(is_breached)
        self.assertEqual(severity, "soft")

    def test_check_limit_nonexistent(self) -> Any:
        """Test checking a non-existent position limit."""
        with self.assertRaises(KeyError):
            self.manager.check_limit("NONEXISTENT", 1000000.0)

    def test_check_limits_by_scope(self) -> Any:
        """Test checking all limits for a specific scope and value."""
        self.manager.add_limit(self.limit1)
        self.manager.add_limit(self.limit2)
        results = self.manager.check_limits_by_scope(
            LimitScope.INSTRUMENT, "AAPL", {"notional": 1500000.0}
        )
        self.assertIn("AAPL_NOTIONAL", results)
        self.assertTrue(results["AAPL_NOTIONAL"][0])
        self.assertEqual(results["AAPL_NOTIONAL"][1], "soft")
        results = self.manager.check_limits_by_scope(
            LimitScope.SECTOR, "TECH", {"percentage": 35.0}
        )
        self.assertIn("TECH_SECTOR", results)
        self.assertTrue(results["TECH_SECTOR"][0])
        self.assertEqual(results["TECH_SECTOR"][1], "soft")

    def test_get_active_breaches(self) -> Any:
        """Test getting all active limit breaches."""
        self.manager.add_limit(self.limit1)
        self.manager.add_limit(self.limit2)
        self.manager.check_limit("AAPL_NOTIONAL", 1500000.0)
        self.manager.check_limit("TECH_SECTOR", 35.0)
        breaches = self.manager.get_active_breaches()
        self.assertEqual(len(breaches), 2)
        self.assertIn("AAPL_NOTIONAL", breaches)
        self.assertIn("TECH_SECTOR", breaches)
        soft_breaches = self.manager.get_active_breaches(severity="soft")
        self.assertEqual(len(soft_breaches), 2)
        hard_breaches = self.manager.get_active_breaches(severity="hard")
        self.assertEqual(len(hard_breaches), 0)

    def test_clear_breach(self) -> Any:
        """Test clearing a specific breach."""
        self.manager.add_limit(self.limit1)
        self.manager.check_limit("AAPL_NOTIONAL", 1500000.0)
        result = self.manager.clear_breach("AAPL_NOTIONAL")
        self.assertTrue(result)
        self.assertEqual(len(self.manager.breaches), 0)

    def test_clear_specific_breach(self) -> Any:
        """Test clearing a specific breach from multiple breaches."""
        self.manager.add_limit(self.limit1)
        self.manager.check_limit("AAPL_NOTIONAL", 1500000.0)
        self.manager.check_limit("AAPL_NOTIONAL", 1600000.0)
        result = self.manager.clear_breach("AAPL_NOTIONAL", 0)
        self.assertTrue(result)
        self.assertEqual(len(self.manager.breaches["AAPL_NOTIONAL"]), 1)

    def test_clear_nonexistent_breach(self) -> Any:
        """Test clearing a non-existent breach."""
        result = self.manager.clear_breach("NONEXISTENT")
        self.assertFalse(result)

    def test_generate_limits_report(self) -> Any:
        """Test generating a comprehensive report on position limits and breaches."""
        self.manager.add_limit(self.limit1)
        self.manager.add_limit(self.limit2)
        self.manager.check_limit("AAPL_NOTIONAL", 1500000.0)
        report = self.manager.generate_limits_report()
        self.assertIn("limits", report)
        self.assertIn("active_breaches", report)
        self.assertIn("breach_details", report)
        self.assertIn("AAPL_NOTIONAL", report["limits"])
        self.assertIn("TECH_SECTOR", report["limits"])
        self.assertEqual(report["active_breaches"], 1)
        self.assertIn("AAPL_NOTIONAL", report["breach_details"])
        self.assertTrue(report["limits"]["AAPL_NOTIONAL"]["has_breaches"])
        self.assertFalse(report["limits"]["TECH_SECTOR"]["has_breaches"])


if __name__ == "__main__":
    unittest.main()
