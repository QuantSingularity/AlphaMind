"""
## Reconnection Manager Module.
#
## This module provides robust reconnection logic for market venue connections,
## handling automatic reconnection attempts with exponential backoff, circuit breaking,
## and connection health monitoring.
"""

import datetime
import logging
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ReconnectionState(Enum):
    """States for the reconnection process."""

    IDLE = "idle"
    ATTEMPTING = "attempting"
    BACKOFF = "backoff"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class ReconnectionStats:
    """Statistics for reconnection attempts."""

    total_attempts: int = 0
    successful_reconnects: int = 0
    failed_attempts: int = 0
    last_attempt_time: Optional[datetime.datetime] = None
    last_success_time: Optional[datetime.datetime] = None
    last_failure_time: Optional[datetime.datetime] = None
    consecutive_failures: int = 0
    average_reconnect_time: float = 0.0
    total_downtime: float = 0.0


class ReconnectionConfig:
    """Configuration for reconnection behavior."""

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        max_attempts: int = 0,
        circuit_break_threshold: int = 5,
        circuit_break_timeout: float = 300.0,
        health_check_interval: float = 30.0,
    ) -> None:
        """
        Initialize reconnection configuration.

        Args:
            initial_delay: Initial delay between reconnection attempts in seconds
            max_delay: Maximum delay between reconnection attempts in seconds
            backoff_factor: Multiplier for exponential backoff
            jitter: Random jitter factor to add to delay (0.1 = 10%)
            max_attempts: Maximum number of reconnection attempts (0 = unlimited)
            circuit_break_threshold: Number of consecutive failures before circuit breaking
            circuit_break_timeout: Time in seconds to wait before resetting circuit breaker
            health_check_interval: Interval in seconds for connection health checks
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.max_attempts = max_attempts
        self.circuit_break_threshold = circuit_break_threshold
        self.circuit_break_timeout = circuit_break_timeout
        self.health_check_interval = health_check_interval


class ReconnectionManager:
    """
    Manages reconnection attempts for market venue connections with
    exponential backoff, jitter, and circuit breaking.
    """

    def __init__(self, config: Optional[ReconnectionConfig] = None) -> None:
        """
        Initialize reconnection manager.

        Args:
            config: Reconnection configuration (optional, uses defaults if not provided)
        """
        self.config = config or ReconnectionConfig()
        self.state = ReconnectionState.IDLE
        self.stats = ReconnectionStats()
        self.current_delay = self.config.initial_delay
        self.circuit_break_until: Optional[datetime.datetime] = None
        self.reconnect_timer: Optional[threading.Timer] = None
        self.health_check_timer: Optional[threading.Timer] = None
        self.is_running = False
        self.connection_id: Optional[str] = None
        self.connect_callback: Optional[Callable[[], bool]] = None
        self.health_check_callback: Optional[Callable[[], bool]] = None
        self.on_reconnect_callback: Optional[Callable[[bool], None]] = None
        self.on_give_up_callback: Optional[Callable[[], None]] = None
        self.last_connection_time: Optional[datetime.datetime] = None
        self.disconnect_time: Optional[datetime.datetime] = None
        logger.info("Reconnection manager initialized")

    def start(
        self,
        connection_id: str,
        connect_callback: Callable[[], bool],
        health_check_callback: Optional[Callable[[], bool]] = None,
        on_reconnect_callback: Optional[Callable[[bool], None]] = None,
        on_give_up_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Start the reconnection manager for a specific connection.

        Args:
            connection_id: Identifier for the connection
            connect_callback: Function to call to attempt reconnection
            health_check_callback: Function to call to check connection health
            on_reconnect_callback: Function to call after reconnection attempt
            on_give_up_callback: Function to call when giving up on reconnection
        """
        if self.is_running:
            logger.warning(
                f"Reconnection manager for {self.connection_id} is already running"
            )
            return
        self.connection_id = connection_id
        self.connect_callback = connect_callback
        self.health_check_callback = health_check_callback
        self.on_reconnect_callback = on_reconnect_callback
        self.on_give_up_callback = on_give_up_callback
        self.is_running = True
        self.state = ReconnectionState.IDLE
        if self.health_check_callback:
            self._start_health_check_timer()
        logger.info(f"Reconnection manager started for connection {connection_id}")

    def stop(self) -> None:
        """Stop the reconnection manager."""
        if not self.is_running:
            return
        self.is_running = False
        self._cancel_timers()
        self.state = ReconnectionState.IDLE
        logger.info(f"Reconnection manager stopped for connection {self.connection_id}")

    def connection_lost(self) -> None:
        """
        Notify the reconnection manager that the connection has been lost.
        This will trigger the reconnection process.
        """
        if not self.is_running:
            logger.warning(
                f"Reconnection manager for {self.connection_id} is not running"
            )
            return
        self.disconnect_time = datetime.datetime.now()
        logger.info(
            f"Connection lost for {self.connection_id}, initiating reconnection"
        )
        if self.state == ReconnectionState.IDLE:
            self.current_delay = self.config.initial_delay
        self._attempt_reconnection()

    def connection_established(self) -> None:
        """
        Notify the reconnection manager that the connection has been established.
        This will reset the reconnection state.
        """
        self.last_connection_time = datetime.datetime.now()
        if self.disconnect_time:
            downtime = (
                self.last_connection_time - self.disconnect_time
            ).total_seconds()
            self.stats.total_downtime += downtime
            logger.info(
                f"Connection {self.connection_id} restored after {downtime:.2f}s downtime"
            )
            self.disconnect_time = None
        self.state = ReconnectionState.IDLE
        self.current_delay = self.config.initial_delay
        self.stats.consecutive_failures = 0
        self._cancel_timers()
        logger.info(
            f"Connection established for {self.connection_id}, reconnection state reset"
        )

    def _attempt_reconnection(self) -> None:
        """Attempt to reconnect with the current settings."""
        if not self.is_running:
            return
        if self.state == ReconnectionState.CIRCUIT_OPEN:
            if datetime.datetime.now() < self.circuit_break_until:
                logger.info(
                    f"Circuit breaker open for {self.connection_id}, skipping reconnection attempt"
                )
                return
            else:
                logger.info(
                    f"Circuit breaker timeout elapsed for {self.connection_id}, resetting"
                )
                self.state = ReconnectionState.IDLE
                self.stats.consecutive_failures = 0
        if (
            self.config.max_attempts > 0
            and self.stats.total_attempts >= self.config.max_attempts
        ):
            logger.warning(
                f"Maximum reconnection attempts ({self.config.max_attempts}) reached for {self.connection_id}"
            )
            if self.on_give_up_callback:
                self.on_give_up_callback()
            return
        self.state = ReconnectionState.ATTEMPTING
        self.stats.total_attempts += 1
        self.stats.last_attempt_time = datetime.datetime.now()
        logger.info(
            f"Attempting reconnection for {self.connection_id} (attempt {self.stats.total_attempts})"
        )
        try:
            start_time = time.time()
            success = self.connect_callback()
            elapsed = time.time() - start_time
            if success:
                self.stats.successful_reconnects += 1
                self.stats.last_success_time = datetime.datetime.now()
                if self.stats.successful_reconnects == 1:
                    self.stats.average_reconnect_time = elapsed
                else:
                    self.stats.average_reconnect_time = (
                        self.stats.average_reconnect_time
                        * (self.stats.successful_reconnects - 1)
                        + elapsed
                    ) / self.stats.successful_reconnects
                logger.info(
                    f"Reconnection successful for {self.connection_id} in {elapsed:.2f}s"
                )
                self.connection_established()
                if self.on_reconnect_callback:
                    self.on_reconnect_callback(True)
            else:
                self._handle_reconnection_failure()
        except Exception as e:
            logger.error(
                f"Error during reconnection attempt for {self.connection_id}: {str(e)}"
            )
            self._handle_reconnection_failure()

    def _handle_reconnection_failure(self) -> None:
        """Handle a failed reconnection attempt."""
        self.stats.failed_attempts += 1
        self.stats.consecutive_failures += 1
        self.stats.last_failure_time = datetime.datetime.now()
        logger.warning(
            f"Reconnection failed for {self.connection_id} (consecutive failures: {self.stats.consecutive_failures})"
        )
        if self.stats.consecutive_failures >= self.config.circuit_break_threshold:
            self.state = ReconnectionState.CIRCUIT_OPEN
            self.circuit_break_until = datetime.datetime.now() + datetime.timedelta(
                seconds=self.config.circuit_break_timeout
            )
            logger.warning(
                f"Circuit breaker triggered for {self.connection_id}, pausing reconnection attempts until {self.circuit_break_until}"
            )
            self._schedule_reconnection(self.config.circuit_break_timeout)
        else:
            self.state = ReconnectionState.BACKOFF
            jitter_amount = self.current_delay * self.config.jitter
            actual_delay = self.current_delay + random.uniform(
                -jitter_amount, jitter_amount
            )
            actual_delay = max(self.config.initial_delay, actual_delay)
            logger.info(
                f"Backing off for {actual_delay:.2f}s before next reconnection attempt for {self.connection_id}"
            )
            self._schedule_reconnection(actual_delay)
            self.current_delay = min(
                self.current_delay * self.config.backoff_factor, self.config.max_delay
            )
        if self.on_reconnect_callback:
            self.on_reconnect_callback(False)

    def _schedule_reconnection(self, delay: float) -> None:
        """
        Schedule a reconnection attempt after a delay.

        Args:
            delay: Delay in seconds
        """
        self._cancel_timers()
        self.reconnect_timer = threading.Timer(delay, self._attempt_reconnection)
        self.reconnect_timer.daemon = True
        self.reconnect_timer.start()

    def _start_health_check_timer(self) -> None:
        """Start the health check timer."""
        if not self.health_check_callback or not self.is_running:
            return
        self.health_check_timer = threading.Timer(
            self.config.health_check_interval, self._perform_health_check
        )
        self.health_check_timer.daemon = True
        self.health_check_timer.start()

    def _perform_health_check(self) -> None:
        """Perform a health check on the connection."""
        if not self.is_running or not self.health_check_callback:
            return
        try:
            if self.state == ReconnectionState.IDLE:
                logger.debug(
                    f"Performing health check for connection {self.connection_id}"
                )
                is_healthy = self.health_check_callback()
                if not is_healthy:
                    logger.warning(
                        f"Health check failed for connection {self.connection_id}, initiating reconnection"
                    )
                    self.connection_lost()
        except Exception as e:
            logger.error(
                f"Error during health check for {self.connection_id}: {str(e)}"
            )
            self.connection_lost()
        finally:
            if self.is_running:
                self._start_health_check_timer()

    def _cancel_timers(self) -> None:
        """Cancel any active timers."""
        if self.reconnect_timer:
            self.reconnect_timer.cancel()
            self.reconnect_timer = None
        if self.health_check_timer:
            self.health_check_timer.cancel()
            self.health_check_timer = None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get reconnection statistics.

        Returns:
            Dictionary containing reconnection statistics
        """
        return {
            "connection_id": self.connection_id,
            "state": self.state.value,
            "total_attempts": self.stats.total_attempts,
            "successful_reconnects": self.stats.successful_reconnects,
            "failed_attempts": self.stats.failed_attempts,
            "consecutive_failures": self.stats.consecutive_failures,
            "last_attempt_time": (
                self.stats.last_attempt_time.isoformat()
                if self.stats.last_attempt_time
                else None
            ),
            "last_success_time": (
                self.stats.last_success_time.isoformat()
                if self.stats.last_success_time
                else None
            ),
            "last_failure_time": (
                self.stats.last_failure_time.isoformat()
                if self.stats.last_failure_time
                else None
            ),
            "average_reconnect_time": self.stats.average_reconnect_time,
            "total_downtime": self.stats.total_downtime,
            "circuit_break_until": (
                self.circuit_break_until.isoformat()
                if self.circuit_break_until
                else None
            ),
            "current_delay": self.current_delay,
        }
