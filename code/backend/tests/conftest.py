import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_PATH = os.path.join(BASE_DIR, "..")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)


@pytest.fixture
def sample_market_data() -> Any:
    """Fixture providing sample market data for testing."""
    return {
        "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN"],
        "prices": {
            "AAPL": [150.25, 151.3, 149.8, 152.5, 153.65],
            "MSFT": [290.1, 292.15, 289.75, 295.2, 297.3],
            "GOOGL": [2750.25, 2780.5, 2745.3, 2790.1, 2810.25],
            "AMZN": [3350.5, 3375.25, 3340.1, 3390.75, 3410.2],
        },
        "volumes": {
            "AAPL": [5000000, 6200000, 4800000, 5500000, 6000000],
            "MSFT": [3200000, 3500000, 3100000, 3600000, 3800000],
            "GOOGL": [1200000, 1350000, 1150000, 1300000, 1400000],
            "AMZN": [2100000, 2300000, 2000000, 2200000, 2400000],
        },
        "timestamps": [
            "2025-04-25T09:30:00",
            "2025-04-25T10:30:00",
            "2025-04-25T11:30:00",
            "2025-04-25T12:30:00",
            "2025-04-25T13:30:00",
        ],
    }


@pytest.fixture
def mock_authentication_token() -> Any:
    """Fixture providing a mock authentication JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFscGhhTWluZCBUZXN0IFVzZXIiLCJpYXQiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
