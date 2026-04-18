"""
AlphaMind Core Package.

Defines the fundamental domain primitives and abstract base class used
throughout the AlphaMind system:

- MarketData  — standard container for processed time series data
- Signal      — standard container for trading signals
- BaseModule  — abstract lifecycle base class for all functional modules

Configuration management lives in core.config (ConfigManager).
Exception hierarchy lives in core.exceptions.
"""

import abc
import datetime
import logging
from typing import Any, Dict, Optional, Union

import pandas as pd
from core.config import ConfigManager  # single source of truth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("AlphaMind.Core")


class MarketData:
    """Standard container for processed market and alternative data."""

    def __init__(self, data: pd.DataFrame, source: str = "combined") -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("MarketData must be initialized with a Pandas DataFrame.")
        self.data = data
        self.source = source
        logger.debug(
            f"MarketData created from source: {source} with {len(data)} records."
        )

    def get_latest(self) -> Dict[str, Any]:
        """Return the latest data point as a dictionary."""
        if self.data.empty:
            return {}
        return self.data.iloc[-1].to_dict()


class Signal:
    """Standard container for trading signals."""

    def __init__(
        self,
        ticker: str,
        position: int,
        confidence: float,
        timestamp: datetime.datetime,
    ) -> None:
        self.ticker = ticker
        self.position = position
        self.confidence = confidence
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Union[str, int, float]]:
        """Return the signal as a serialisable dictionary."""
        return {
            "ticker": self.ticker,
            "position": self.position,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseModule(abc.ABC):
    """
    Abstract base class for all functional modules in the AlphaMind system.
    Enforces a standard lifecycle: configure → run.
    """

    def __init__(self, module_name: str, config_manager: ConfigManager) -> None:
        self.module_name = module_name
        self.config = config_manager
        self.logger = logging.getLogger(f"AlphaMind.{module_name}")
        self.logger.info(f"Initializing {self.module_name}...")
        self.is_configured = False

    @abc.abstractmethod
    def configure(self) -> bool:
        """Perform setup and validate configuration. Must be called before run()."""
        self.is_configured = True
        self.logger.info(f"{self.module_name} configured.")
        return True

    @abc.abstractmethod
    def run(
        self, input_data: Optional[Union[MarketData, Signal]] = None
    ) -> Union[MarketData, Signal, None]:
        """Execute the primary logic of the module."""
        if not self.is_configured:
            self.logger.error(f"{self.module_name} must be configured before running.")
            return None
        self.logger.info(f"Running {self.module_name}.")
        return None


__all__ = ["MarketData", "Signal", "BaseModule", "ConfigManager"]
