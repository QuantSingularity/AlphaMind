"""
Position Limits Management Module.

This module provides functionality for defining, monitoring, and enforcing
position limits across different asset classes and risk factors.
"""

import datetime
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LimitType(Enum):
    """Types of position limits that can be enforced."""

    NOTIONAL = "notional"
    QUANTITY = "quantity"
    PERCENTAGE = "percentage"
    RISK_FACTOR = "risk_factor"
    VAR = "var"


class LimitScope(Enum):
    """Scope of position limits."""

    INSTRUMENT = "instrument"
    ASSET_CLASS = "asset_class"
    SECTOR = "sector"
    COUNTRY = "country"
    PORTFOLIO = "portfolio"
    STRATEGY = "strategy"


@dataclass
class PositionLimit:
    """Position limit configuration."""

    limit_id: str
    limit_type: LimitType
    scope: LimitScope
    scope_value: str
    soft_limit: float
    hard_limit: float
    description: str = ""
    active: bool = True
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    def is_breached(self, value: float) -> Tuple[bool, str]:
        """Check if a value breaches the position limits."""
        if not self.active:
            return (False, "none")
        if value > self.hard_limit:
            return (True, "hard")
        elif value > self.soft_limit:
            return (True, "soft")
        return (False, "none")


class PositionLimitsManager:
    """Manages position limits across the system."""

    def __init__(self) -> None:
        """Initialize position limits manager."""
        self.limits: Dict[str, PositionLimit] = {}
        self.breaches: Dict[str, List[Dict]] = {}

    def add_limit(self, limit: PositionLimit) -> None:
        """Add a new position limit."""
        if limit.limit_id in self.limits:
            logger.warning(
                f"Overwriting existing position limit with ID {limit.limit_id}"
            )
        self.limits[limit.limit_id] = limit
        logger.info(
            f"Added position limit {limit.limit_id} for {limit.scope.value}:{limit.scope_value}"
        )

    def remove_limit(self, limit_id: str) -> bool:
        """Remove a position limit."""
        if limit_id in self.limits:
            del self.limits[limit_id]
            logger.info(f"Removed position limit {limit_id}")
            return True
        logger.warning(f"Attempted to remove non-existent position limit {limit_id}")
        return False

    def update_limit(self, limit_id: str, **kwargs) -> bool:
        """Update an existing position limit."""
        if limit_id not in self.limits:
            logger.warning(
                f"Attempted to update non-existent position limit {limit_id}"
            )
            return False
        limit = self.limits[limit_id]
        for key, value in kwargs.items():
            if hasattr(limit, key):
                setattr(limit, key, value)
            else:
                logger.warning(
                    f"Ignoring unknown attribute {key} for position limit {limit_id}"
                )
        limit.updated_at = datetime.datetime.now()
        logger.info(f"Updated position limit {limit_id}")
        return True

    def check_limit(self, limit_id: str, value: float) -> Tuple[bool, str]:
        """Check a specific position limit."""
        if limit_id not in self.limits:
            raise KeyError(f"Position limit {limit_id} not found")
        limit = self.limits[limit_id]
        is_breached, severity = limit.is_breached(value)
        if is_breached:
            breach = {
                "limit_id": limit_id,
                "value": value,
                "severity": severity,
                "timestamp": datetime.datetime.now(),
            }
            if limit_id not in self.breaches:
                self.breaches[limit_id] = []
            self.breaches[limit_id].append(breach)
            logger.warning(
                f"Position limit breach for {limit_id} ({limit.scope.value}:{limit.scope_value}): {value} exceeds {severity} limit of {(limit.soft_limit if severity == 'soft' else limit.hard_limit)}"
            )
        return (is_breached, severity)

    def check_limits_by_scope(
        self, scope: LimitScope, scope_value: str, values: Dict[str, float]
    ) -> Dict[str, Tuple[bool, str]]:
        """Check all limits for a specific scope and value."""
        results: Dict[str, Any] = {}
        for limit_id, limit in self.limits.items():
            if limit.scope == scope and limit.scope_value == scope_value:
                if limit.limit_type.value in values:
                    value = values[limit.limit_type.value]
                    results[limit_id] = self.check_limit(limit_id, value)
        return results

    def get_active_breaches(
        self, severity: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """Get all active limit breaches."""
        if severity is None:
            return self.breaches
        filtered_breaches: Dict[str, Any] = {}
        for limit_id, breach_list in self.breaches.items():
            filtered = [b for b in breach_list if b["severity"] == severity]
            if filtered:
                filtered_breaches[limit_id] = filtered
        return filtered_breaches

    def clear_breach(self, limit_id: str, breach_index: Optional[int] = None) -> bool:
        """Clear a specific breach or all breaches for a limit."""
        if limit_id not in self.breaches:
            return False
        if breach_index is not None:
            if 0 <= breach_index < len(self.breaches[limit_id]):
                self.breaches[limit_id].pop(breach_index)
                if not self.breaches[limit_id]:
                    del self.breaches[limit_id]
                logger.info(
                    f"Cleared breach {breach_index} for position limit {limit_id}"
                )
                return True
            return False
        else:
            del self.breaches[limit_id]
            logger.info(f"Cleared all breaches for position limit {limit_id}")
            return True

    def generate_limits_report(self) -> Dict:
        """Generate a comprehensive report on position limits and breaches."""
        report = {
            "limits": {},
            "active_breaches": len(self.breaches),
            "breach_details": self.breaches.copy(),
        }
        for limit_id, limit in self.limits.items():
            report["limits"][limit_id] = {
                "type": limit.limit_type.value,
                "scope": limit.scope.value,
                "scope_value": limit.scope_value,
                "soft_limit": limit.soft_limit,
                "hard_limit": limit.hard_limit,
                "active": limit.active,
                "has_breaches": limit_id in self.breaches,
            }
        return report
