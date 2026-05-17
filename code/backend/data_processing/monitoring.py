"""
Monitoring module for AlphaMind data processing.

Provides performance tracking and alert generation capabilities.
"""

import datetime
import logging
import statistics
import time
from collections import deque
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Represents a monitoring alert."""

    def __init__(
        self,
        level: AlertLevel,
        message: str,
        metric_name: str,
        value: Any,
        threshold: Any,
        timestamp: Optional[datetime.datetime] = None,
    ) -> None:
        """Initialize alert."""
        self.level = level
        self.message = message
        self.metric_name = metric_name
        self.value = value
        self.threshold = threshold
        self.timestamp = timestamp or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "level": self.level.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricCollector:
    """Collects and aggregates performance metrics."""

    def __init__(self, name: str, max_history: int = 1000) -> None:
        """
        Initialize metric collector.

        Args:
            name: Name of the metric
            max_history: Maximum number of historical values to keep
        """
        self.name = name
        self.max_history = max_history
        self.values: deque = deque(maxlen=max_history)
        self.timestamps: deque = deque(maxlen=max_history)

    def record(
        self, value: Union[int, float], timestamp: Optional[float] = None
    ) -> None:
        """
        Record a metric value.

        Args:
            value: Metric value
            timestamp: Timestamp (default: current time)
        """
        self.values.append(value)
        self.timestamps.append(timestamp or time.time())

    def get_latest(self) -> Optional[Union[int, float]]:
        """Get the most recent value."""
        return self.values[-1] if self.values else None

    def get_average(self, window: Optional[int] = None) -> Optional[float]:
        """
        Get average value over window.

        Args:
            window: Number of recent values to average (default: all)

        Returns:
            Average value or None if no values
        """
        if not self.values:
            return None
        values = list(self.values)[-window:] if window else list(self.values)
        return statistics.mean(values)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for the metric."""
        if not self.values:
            return {
                "name": self.name,
                "count": 0,
                "latest": None,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
            }

        values = list(self.values)
        return {
            "name": self.name,
            "count": len(values),
            "latest": values[-1],
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        }


class PerformanceMonitor:
    """Monitors performance metrics and generates alerts."""

    def __init__(self, name: str) -> None:
        """
        Initialize performance monitor.

        Args:
            name: Name of the monitor
        """
        self.name = name
        self.metrics: Dict[str, MetricCollector] = {}
        self.alerts: List[Alert] = []
        self.thresholds: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"Monitor.{name}")

    def register_metric(self, metric_name: str, max_history: int = 1000) -> None:
        """
        Register a new metric for monitoring.

        Args:
            metric_name: Name of the metric
            max_history: Maximum history to keep
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = MetricCollector(metric_name, max_history)
            self.logger.info(f"Registered metric: {metric_name}")

    def set_threshold(
        self,
        metric_name: str,
        threshold_type: str,
        value: Union[int, float],
        alert_level: AlertLevel = AlertLevel.WARNING,
    ) -> None:
        """
        Set a threshold for a metric.

        Args:
            metric_name: Name of the metric
            threshold_type: Type of threshold ('max', 'min', 'avg_max', 'avg_min')
            value: Threshold value
            alert_level: Alert level when threshold is exceeded
        """
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}

        self.thresholds[metric_name][threshold_type] = {
            "value": value,
            "alert_level": alert_level,
        }
        self.logger.info(f"Set {threshold_type} threshold for {metric_name}: {value}")

    def record_metric(self, metric_name: str, value: Union[int, float]) -> None:
        """
        Record a metric value and check thresholds.

        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        # Register metric if not exists
        if metric_name not in self.metrics:
            self.register_metric(metric_name)

        # Record value
        self.metrics[metric_name].record(value)

        # Check thresholds
        self._check_thresholds(metric_name, value)

    def _check_thresholds(self, metric_name: str, value: Union[int, float]) -> None:
        """Check if value exceeds thresholds."""
        if metric_name not in self.thresholds:
            return

        thresholds = self.thresholds[metric_name]
        metric = self.metrics[metric_name]

        # Check max threshold
        if "max" in thresholds and value > thresholds["max"]["value"]:
            self._create_alert(
                metric_name,
                value,
                thresholds["max"]["value"],
                thresholds["max"]["alert_level"],
                f"{metric_name} exceeded maximum threshold: {value} > {thresholds['max']['value']}",
            )

        # Check min threshold
        if "min" in thresholds and value < thresholds["min"]["value"]:
            self._create_alert(
                metric_name,
                value,
                thresholds["min"]["value"],
                thresholds["min"]["alert_level"],
                f"{metric_name} below minimum threshold: {value} < {thresholds['min']['value']}",
            )

        # Check average max threshold
        if "avg_max" in thresholds:
            avg = metric.get_average()
            if avg and avg > thresholds["avg_max"]["value"]:
                self._create_alert(
                    metric_name,
                    avg,
                    thresholds["avg_max"]["value"],
                    thresholds["avg_max"]["alert_level"],
                    f"{metric_name} average exceeded threshold: {avg} > {thresholds['avg_max']['value']}",
                )

    def _create_alert(
        self,
        metric_name: str,
        value: Any,
        threshold: Any,
        level: AlertLevel,
        message: str,
    ) -> None:
        """Create and log an alert."""
        alert = Alert(level, message, metric_name, value, threshold)
        self.alerts.append(alert)

        # Log based on level
        if level == AlertLevel.CRITICAL:
            self.logger.critical(message)
        elif level == AlertLevel.ERROR:
            self.logger.error(message)
        elif level == AlertLevel.WARNING:
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def get_metric_stats(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific metric."""
        if metric_name in self.metrics:
            return self.metrics[metric_name].get_stats()
        return None

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all metrics."""
        return {
            "monitor_name": self.name,
            "metrics": {
                name: metric.get_stats() for name, metric in self.metrics.items()
            },
            "alert_count": len(self.alerts),
            "recent_alerts": [alert.to_dict() for alert in self.alerts[-10:]],
        }

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        self.logger.info("Cleared all alerts")


def monitor_execution(monitor: PerformanceMonitor, metric_prefix: str = ""):
    """
    Decorator to monitor function execution time.

    Args:
        monitor: PerformanceMonitor instance
        metric_prefix: Prefix for metric name

    Usage:
        monitor = PerformanceMonitor("my_monitor")

        @monitor_execution(monitor, "processing")
        def process_data(data):
            # Your processing logic
            return result
    """

    def decorator(func: Callable) -> Callable:
        metric_name = (
            f"{metric_prefix}.{func.__name__}" if metric_prefix else func.__name__
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                monitor.record_metric(f"{metric_name}.execution_time", execution_time)
                monitor.record_metric(f"{metric_name}.success_count", 1)
                return result
            except Exception:
                execution_time = time.time() - start_time
                monitor.record_metric(f"{metric_name}.execution_time", execution_time)
                monitor.record_metric(f"{metric_name}.error_count", 1)
                raise

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Public aliases required by data_processing/__init__.py
# ---------------------------------------------------------------------------

#: Alias — AlertManager wraps Alert-creation helpers.
AlertManager = Alert

#: Alias — MetricsCollector is the public name for MetricCollector.
MetricsCollector = MetricCollector

#: Alias — PerformanceTracker is the public name for PerformanceMonitor.
PerformanceTracker = PerformanceMonitor


class PipelineMonitor(PerformanceMonitor):
    """
    Pipeline-scoped performance monitor.

    Thin subclass of :class:`PerformanceMonitor` that pre-tags all metrics
    with a ``pipeline_name`` prefix, making dashboard queries easier.
    """

    def __init__(self, pipeline_name: str, **kwargs) -> None:
        super().__init__(name=f"pipeline.{pipeline_name}", **kwargs)
        self.pipeline_name = pipeline_name
