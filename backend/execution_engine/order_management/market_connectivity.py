"""
## Market Connectivity Module.

## This module extends the base market connectivity module with robust reconnection logic,
## failure simulation capabilities, and improved error handling for stable market connections.
"""

import datetime
import logging
import random
import threading
import time
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from execution_engine.order_management.market_connectivity_base import (
    ConnectionStatus,
    MarketConnectivityManager,
    MarketDataUpdate,
    VenueAdapter,
    VenueConfig,
)
from execution_engine.order_management.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
)

logger = logging.getLogger(__name__)


class VenueType(Enum):
    EXCHANGE = "exchange"
    DARK_POOL = "dark_pool"
    OTC = "otc"


class FailureMode(Enum):
    """Types of simulated failures for testing."""

    DISCONNECT = "disconnect"
    TIMEOUT = "timeout"
    DATA_CORRUPTION = "data_corruption"
    PARTIAL_DATA = "partial_data"
    RATE_LIMIT = "rate_limit"
    HIGH_LATENCY = "high_latency"


class VenueAdapter(VenueAdapter):
    """
    Venue adapter with reconnection logic and failure simulation.
    Extends the base VenueAdapter with robust connection management.
    """

    def __init__(
        self,
        config: VenueConfig,
        reconnection_config: Optional[ReconnectionConfig] = None,
    ) -> None:
        """
        Initialize venue adapter.

        Args:
            config: Venue configuration
            reconnection_config: Configuration for reconnection behavior (optional)
        """
        super().__init__(config)
        self.reconnection_manager = ReconnectionManager(reconnection_config)
        self.failure_simulation_enabled = False
        self.failure_modes = {}
        self.failure_probabilities = {}
        self.last_health_check = None
        self.health_check_interval = 30.0
        self.health_check_thread = None
        self.health_check_running = False
        self.last_activity_time = None
        self.connection_timeout = 60.0
        self.heartbeat_interval = 15.0
        self.heartbeat_thread = None
        self.heartbeat_running = False
        self.messages_sent = 0
        self.messages_received = 0
        self.connection_attempts = 0
        self.successful_connections = 0
        self.connection_failures = 0
        self.last_error_time = None
        self.error_count = 0
        logger.info(f"Venue adapter initialized for {config.venue_id}")

    def connect(self) -> bool:
        """
        Connect to the venue with enhanced error handling and reconnection support.

        Returns:
            True if connection was successful, False otherwise
        """
        self.connection_attempts += 1
        if not self.reconnection_manager.is_running:
            self.reconnection_manager.start(
                connection_id=self.config.venue_id,
                connect_callback=self._connect_with_monitoring,
                health_check_callback=self._check_connection_health,
                on_reconnect_callback=self._handle_reconnection_result,
                on_give_up_callback=self._handle_reconnection_give_up,
            )
        success = self._connect_with_monitoring()
        if success:
            self._start_health_check()
            self._start_heartbeat()
        return success

    def _connect_with_monitoring(self) -> bool:
        """
        Connect to the venue with monitoring and metrics.

        Returns:
            True if connection was successful, False otherwise
        """
        self.status = ConnectionStatus.CONNECTING
        logger.info(f"Connecting to venue {self.config.venue_id} ({self.config.name})")
        try:
            if self._should_simulate_failure(FailureMode.DISCONNECT):
                logger.info(f"Simulating connection failure for {self.config.venue_id}")
                self.status = ConnectionStatus.ERROR
                self.last_error = "Simulated connection failure"
                self.last_error_time = datetime.datetime.now()
                self.error_count += 1
                self.connection_failures += 1
                return False
            start_time = time.time()
            success = self._connect_impl()
            elapsed = time.time() - start_time
            if success:
                self.status = ConnectionStatus.CONNECTED
                self.connected_at = datetime.datetime.now()
                self.last_activity_time = datetime.datetime.now()
                self.successful_connections += 1
                logger.info(
                    f"Connected to venue {self.config.venue_id} in {elapsed:.2f}s"
                )
            else:
                self.status = ConnectionStatus.ERROR
                self.last_error = "Connection failed"
                self.last_error_time = datetime.datetime.now()
                self.error_count += 1
                self.connection_failures += 1
                logger.error(f"Failed to connect to venue {self.config.venue_id}")
            return success
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            self.last_error_time = datetime.datetime.now()
            self.error_count += 1
            self.connection_failures += 1
            logger.error(f"Error connecting to venue {self.config.venue_id}: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from the venue with enhanced cleanup.

        Returns:
            True if disconnection was successful, False otherwise
        """
        self._stop_health_check()
        self._stop_heartbeat()
        if self.reconnection_manager.is_running:
            self.reconnection_manager.stop()
        return super().disconnect()

    def _check_connection_health(self) -> bool:
        """
        Check if the connection is healthy.

        Returns:
            True if the connection is healthy, False otherwise
        """
        if self.status != ConnectionStatus.CONNECTED:
            return False
        if self.last_activity_time:
            elapsed = (
                datetime.datetime.now() - self.last_activity_time
            ).total_seconds()
            if elapsed > self.connection_timeout:
                logger.warning(
                    f"Connection to {self.config.venue_id} timed out (no activity for {elapsed:.2f}s)"
                )
                return False
        self.last_health_check = datetime.datetime.now()
        if self._should_simulate_failure(FailureMode.TIMEOUT):
            logger.info(f"Simulating health check failure for {self.config.venue_id}")
            return False
        return True

    def _start_health_check(self) -> None:
        """Start the health check thread."""
        if self.health_check_running:
            return
        self.health_check_running = True
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        logger.debug(f"Started health check thread for {self.config.venue_id}")

    def _stop_health_check(self) -> None:
        """Stop the health check thread."""
        self.health_check_running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=1.0)
            self.health_check_thread = None
            logger.debug(f"Stopped health check thread for {self.config.venue_id}")

    def _health_check_loop(self) -> None:
        """Main loop for the health check thread."""
        while self.health_check_running:
            try:
                if self.status == ConnectionStatus.CONNECTED:
                    is_healthy = self._check_connection_health()
                    if not is_healthy:
                        logger.warning(
                            f"Health check failed for {self.config.venue_id}, initiating reconnection"
                        )
                        self.status = ConnectionStatus.ERROR
                        self.reconnection_manager.connection_lost()
            except Exception as e:
                logger.error(
                    f"Error in health check for {self.config.venue_id}: {str(e)}"
                )
            time.sleep(self.health_check_interval)

    def _start_heartbeat(self) -> None:
        """Start the heartbeat thread."""
        if self.heartbeat_running:
            return
        self.heartbeat_running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        logger.debug(f"Started heartbeat thread for {self.config.venue_id}")

    def _stop_heartbeat(self) -> None:
        """Stop the heartbeat thread."""
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1.0)
            self.heartbeat_thread = None
            logger.debug(f"Stopped heartbeat thread for {self.config.venue_id}")

    def _heartbeat_loop(self) -> None:
        """Main loop for the heartbeat thread."""
        while self.heartbeat_running:
            try:
                if self.status == ConnectionStatus.CONNECTED:
                    self._send_heartbeat()
            except Exception as e:
                logger.error(f"Error in heartbeat for {self.config.venue_id}: {str(e)}")
            time.sleep(self.heartbeat_interval)

    def _send_heartbeat(self) -> None:
        """Send a heartbeat message to the venue."""
        logger.debug(f"Sending heartbeat to {self.config.venue_id}")
        self.last_activity_time = datetime.datetime.now()

    def _handle_reconnection_result(self, success: bool) -> None:
        """
        Handle the result of a reconnection attempt.

        Args:
            success: Whether the reconnection was successful
        """
        if success:
            logger.info(f"Reconnection successful for {self.config.venue_id}")
        else:
            logger.warning(f"Reconnection failed for {self.config.venue_id}")

    def _handle_reconnection_give_up(self) -> None:
        """Handle the case when reconnection manager gives up."""
        logger.error(f"Reconnection manager gave up for {self.config.venue_id}")

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity_time = datetime.datetime.now()

    def enable_failure_simulation(self, enabled: bool = True) -> None:
        """
        Enable or disable failure simulation.

        Args:
            enabled: Whether failure simulation should be enabled
        """
        self.failure_simulation_enabled = enabled
        logger.info(
            f"Failure simulation {('enabled' if enabled else 'disabled')} for {self.config.venue_id}"
        )

    def configure_failure_mode(
        self,
        mode: FailureMode,
        probability: float = 0.0,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Configure a failure simulation mode.

        Args:
            mode: Failure mode to configure
            probability: Probability of failure (0.0 to 1.0)
            config: Additional configuration for the failure mode
        """
        self.failure_modes[mode] = config or {}
        self.failure_probabilities[mode] = max(0.0, min(1.0, probability))
        logger.info(
            f"Configured failure mode {mode.value} with probability {probability} for {self.config.venue_id}"
        )

    def _should_simulate_failure(self, mode: FailureMode) -> bool:
        """
        Check if a failure should be simulated.

        Args:
            mode: Failure mode to check

        Returns:
            True if failure should be simulated, False otherwise
        """
        if not self.failure_simulation_enabled:
            return False
        if mode not in self.failure_probabilities:
            return False
        probability = self.failure_probabilities[mode]
        return random.random() < probability

    def submit_order(self, order_data: Dict) -> Tuple[bool, str, Dict]:
        """
        Submit an order to the venue with enhanced error handling.

        Args:
            order_data: Order data

        Returns:
            Tuple of (success, order_id, response_data)
        """
        if self._should_simulate_failure(FailureMode.TIMEOUT):
            logger.info(
                f"Simulating order submission timeout for {self.config.venue_id}"
            )
            return (False, "", {"error": "Simulated timeout"})
        if self._should_simulate_failure(FailureMode.DATA_CORRUPTION):
            logger.info(f"Simulating order data corruption for {self.config.venue_id}")
            corrupted_data = order_data.copy()
            if "price" in corrupted_data:
                corrupted_data["price"] = None
            return (False, "", {"error": "Invalid order data"})
        result = super().submit_order(order_data)
        if result[0] or "error" not in result[2]:
            self.update_activity()
            self.messages_sent += 1
        return result

    def process_market_data(self, data: Dict) -> Optional["MarketDataUpdate"]:
        """
        Process market data with failure simulation and validation.

        Args:
            data: Raw market data

        Returns:
            Processed MarketDataUpdate or None if processing failed
        """
        if self._should_simulate_failure(FailureMode.DATA_CORRUPTION):
            logger.info(f"Simulating market data corruption for {self.config.venue_id}")
            return None
        if self._should_simulate_failure(FailureMode.PARTIAL_DATA):
            logger.info(f"Simulating partial market data for {self.config.venue_id}")
            if "bid" in data:
                del data["bid"]
            if "ask" in data:
                del data["ask"]
        if self._should_simulate_failure(FailureMode.HIGH_LATENCY):
            logger.info(f"Simulating high latency for {self.config.venue_id}")
            time.sleep(random.uniform(0.5, 2.0))
        try:
            required_fields = ["venue_id", "instrument_id", "timestamp"]
            for field in required_fields:
                if field not in data:
                    logger.warning(
                        f"Missing required field {field} in market data from {self.config.venue_id}"
                    )
                    return None
            update = MarketDataUpdate(
                venue_id=data["venue_id"],
                instrument_id=data["instrument_id"],
                timestamp=data["timestamp"],
                bid=data.get("bid"),
                ask=data.get("ask"),
                last=data.get("last"),
                volume=data.get("volume"),
                bid_size=data.get("bid_size"),
                ask_size=data.get("ask_size"),
                depth=data.get("depth"),
                metadata=data.get("metadata", {}),
            )
            self.update_activity()
            self.messages_received += 1
            return update
        except Exception as e:
            logger.error(
                f"Error processing market data from {self.config.venue_id}: {str(e)}"
            )
            return None

    def get_status(self) -> Dict:
        """
        Get enhanced status information.

        Returns:
            Dictionary containing status information
        """
        base_status = super().get_status()
        enhanced_status = {
            **base_status,
            "last_activity_time": (
                self.last_activity_time.isoformat() if self.last_activity_time else None
            ),
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "connection_failures": self.connection_failures,
            "error_count": self.error_count,
            "last_error_time": (
                self.last_error_time.isoformat() if self.last_error_time else None
            ),
            "failure_simulation_enabled": self.failure_simulation_enabled,
            "failure_modes": {
                mode.value: prob for mode, prob in self.failure_probabilities.items()
            },
        }
        if self.reconnection_manager.is_running:
            enhanced_status["reconnection"] = self.reconnection_manager.get_stats()
        return enhanced_status


class MarketConnectivityManager(MarketConnectivityManager):
    """
    Market connectivity manager with improved connection handling,
    failure simulation, and monitoring capabilities.
    """

    def __init__(self) -> None:
        """Initialize enhanced market connectivity manager."""
        super().__init__()
        self.global_failure_simulation_enabled = False
        self.connection_monitor_thread = None
        self.connection_monitor_running = False
        self.connection_monitor_interval = 60.0
        self.status_history = []
        self.max_status_history = 100
        logger.info("Enhanced market connectivity manager initialized")

    def add_venue(self, config: VenueConfig, adapter_class: Any = VenueAdapter) -> None:
        """
        Add a new venue with enhanced adapter.

        Args:
            config: Venue configuration
            adapter_class: Class to use for the venue adapter (default: VenueAdapter)
        """
        super().add_venue(config, adapter_class)

    def enable_global_failure_simulation(self, enabled: bool = True) -> None:
        """
        Enable or disable failure simulation globally for all venues.

        Args:
            enabled: Whether failure simulation should be enabled
        """
        self.global_failure_simulation_enabled = enabled
        for venue_id, venue in self.venues.items():
            if isinstance(venue, VenueAdapter):
                venue.enable_failure_simulation(enabled)
        logger.info(
            f"Global failure simulation {('enabled' if enabled else 'disabled')}"
        )

    def configure_venue_failure(
        self,
        venue_id: str,
        mode: FailureMode,
        probability: float = 0.0,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Configure failure simulation for a specific venue.

        Args:
            venue_id: ID of the venue
            mode: Failure mode to configure
            probability: Probability of failure (0.0 to 1.0)
            config: Additional configuration for the failure mode

        Returns:
            True if configuration was successful, False otherwise
        """
        if venue_id not in self.venues:
            logger.warning(f"Venue {venue_id} not found")
            return False
        venue = self.venues[venue_id]
        if not isinstance(venue, VenueAdapter):
            logger.warning(f"Venue {venue_id} is not an VenueAdapter")
            return False
        venue.configure_failure_mode(mode, probability, config)
        return True

    def start_connection_monitoring(self) -> None:
        """Start the connection monitoring thread."""
        if self.connection_monitor_running:
            logger.warning("Connection monitoring is already running")
            return
        self.connection_monitor_running = True
        self.connection_monitor_thread = threading.Thread(
            target=self._connection_monitor_loop
        )
        self.connection_monitor_thread.daemon = True
        self.connection_monitor_thread.start()
        logger.info("Started connection monitoring")

    def stop_connection_monitoring(self) -> None:
        """Stop the connection monitoring thread."""
        if not self.connection_monitor_running:
            logger.warning("Connection monitoring is not running")
            return
        self.connection_monitor_running = False
        if self.connection_monitor_thread:
            self.connection_monitor_thread.join(timeout=5.0)
        logger.info("Stopped connection monitoring")

    def _connection_monitor_loop(self) -> None:
        """Main loop for the connection monitoring thread."""
        while self.connection_monitor_running:
            try:
                statuses = self.get_all_venue_statuses()
                timestamp = datetime.datetime.now().isoformat()
                history_entry = {"timestamp": timestamp, "statuses": statuses}
                self.status_history.append(history_entry)
                if len(self.status_history) > self.max_status_history:
                    self.status_history = self.status_history[
                        -self.max_status_history :
                    ]
                for venue_id, status in statuses.items():
                    if (
                        status["status"] != "connected"
                        and self.venues[venue_id].config.enabled
                    ):
                        logger.warning(
                            f"Venue {venue_id} is not connected, attempting reconnection"
                        )
                        venue = self.venues[venue_id]
                        if isinstance(venue, VenueAdapter):
                            venue.reconnection_manager.connection_lost()
            except Exception as e:
                logger.error(f"Error in connection monitoring: {str(e)}")
            time.sleep(self.connection_monitor_interval)

    def get_connection_health_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive health report for all connections.

        Returns:
            Dictionary containing health report
        """
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "venues": {},
            "overall_status": "healthy",
            "connected_venues": 0,
            "total_venues": len(self.venues),
            "failure_simulation_enabled": self.global_failure_simulation_enabled,
        }
        for venue_id, venue in self.venues.items():
            venue_status = venue.get_status()
            if isinstance(venue, VenueAdapter):
                venue_health = {
                    "status": venue_status["status"],
                    "enabled": venue_status["enabled"],
                    "last_activity": venue_status.get("last_activity_time"),
                    "messages_received": venue_status.get("messages_received", 0),
                    "messages_sent": venue_status.get("messages_sent", 0),
                    "error_count": venue_status.get("error_count", 0),
                    "reconnection_attempts": venue_status.get("reconnection", {}).get(
                        "total_attempts", 0
                    ),
                    "failure_simulation": venue_status.get(
                        "failure_simulation_enabled", False
                    ),
                }
            else:
                venue_health = {
                    "status": venue_status["status"],
                    "enabled": venue_status["enabled"],
                }
            report["venues"][venue_id] = venue_health
            if venue_status["status"] == "connected":
                report["connected_venues"] += 1
        enabled_venues = sum(
            (1 for venue_id, venue in self.venues.items() if venue.config.enabled)
        )
        if report["connected_venues"] < enabled_venues:
            report["overall_status"] = "degraded"
        if report["connected_venues"] == 0 and enabled_venues > 0:
            report["overall_status"] = "critical"
        return report

    def simulate_venue_failure(self, venue_id: str) -> bool:
        """
        Simulate a complete failure for a specific venue.

        Args:
            venue_id: ID of the venue to fail

        Returns:
            True if simulation was triggered, False otherwise
        """
        if venue_id not in self.venues:
            logger.warning(f"Venue {venue_id} not found")
            return False
        venue = self.venues[venue_id]
        if venue.status != ConnectionStatus.CONNECTED:
            logger.warning(
                f"Venue {venue_id} is not connected, cannot simulate failure"
            )
            return False
        logger.info(f"Simulating complete failure for venue {venue_id}")
        venue.status = ConnectionStatus.ERROR
        venue.last_error = "Simulated complete failure"
        venue.last_error_time = datetime.datetime.now()
        if isinstance(venue, VenueAdapter):
            venue.reconnection_manager.connection_lost()
        return True

    def simulate_market_data_issue(
        self, venue_id: str, issue_type: FailureMode
    ) -> bool:
        """
        Simulate a market data issue for a specific venue.

        Args:
            venue_id: ID of the venue
            issue_type: Type of issue to simulate

        Returns:
            True if simulation was triggered, False otherwise
        """
        if venue_id not in self.venues:
            logger.warning(f"Venue {venue_id} not found")
            return False
        venue = self.venues[venue_id]
        if not isinstance(venue, VenueAdapter):
            logger.warning(f"Venue {venue_id} is not an VenueAdapter")
            return False
        venue.enable_failure_simulation(True)
        venue.configure_failure_mode(issue_type, 1.0)
        logger.info(f"Simulated {issue_type.value} issue for venue {venue_id}")
        return True

    def reset_failure_simulations(self) -> None:
        """Reset all failure simulations to disabled state."""
        self.global_failure_simulation_enabled = False
        for venue_id, venue in self.venues.items():
            if isinstance(venue, VenueAdapter):
                venue.enable_failure_simulation(False)
        logger.info("Reset all failure simulations")
