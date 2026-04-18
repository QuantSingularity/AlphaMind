"""Tests for SatelliteFeatureExtractor — simulation mode (no API credentials needed)."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../../.."))

from code.backend.analytics.alternative_data.satellite_processing import (
    SatelliteFeatureExtractor,
)


@pytest.fixture
def extractor() -> SatelliteFeatureExtractor:
    return SatelliteFeatureExtractor(simulation_mode=True)


class TestInit:
    def test_simulation_mode(self, extractor: SatelliteFeatureExtractor) -> None:
        assert extractor.simulation_mode is True

    def test_model_none_in_simulation(
        self, extractor: SatelliteFeatureExtractor
    ) -> None:
        assert extractor.model is None

    def test_raises_without_credentials(self) -> None:
        with pytest.raises(ValueError):
            SatelliteFeatureExtractor(simulation_mode=False)


class TestProcessGeospatial:
    def test_returns_series(self, extractor: SatelliteFeatureExtractor) -> None:
        r = extractor.process_geospatial(
            [-122.009, 37.334, -121.988, 37.345], "2022-01-01/2022-06-30"
        )
        assert isinstance(r, pd.Series)

    def test_values_unit_interval(self, extractor: SatelliteFeatureExtractor) -> None:
        r = extractor.process_geospatial(
            [-122.009, 37.334, -121.988, 37.345], "2022-01-01/2022-12-31"
        )
        assert (r >= 0.0).all() and (r <= 1.0).all()

    def test_non_empty(self, extractor: SatelliteFeatureExtractor) -> None:
        r = extractor.process_geospatial(
            [-122.009, 37.334, -121.988, 37.345], "2022-01-01/2022-03-31"
        )
        assert len(r) > 0


class TestCreateTimeseries:
    def test_known_ticker(self, extractor: SatelliteFeatureExtractor) -> None:
        df = extractor.create_timeseries("AAPL", "2022-01-01/2022-06-30")
        assert isinstance(df, pd.DataFrame) and not df.empty

    def test_tsla_multiple_facilities(
        self, extractor: SatelliteFeatureExtractor
    ) -> None:
        df = extractor.create_timeseries("TSLA", "2022-01-01/2022-06-30")
        assert df.shape[1] >= 2

    def test_unknown_ticker_empty(self, extractor: SatelliteFeatureExtractor) -> None:
        df = extractor.create_timeseries("ZZZZ", "2022-01-01/2022-06-30")
        assert df.empty

    def test_case_insensitive(self, extractor: SatelliteFeatureExtractor) -> None:
        df1 = extractor.create_timeseries("AAPL", "2022-01-01/2022-03-31")
        df2 = extractor.create_timeseries("aapl", "2022-01-01/2022-03-31")
        assert list(df1.columns) == list(df2.columns)

    def test_values_unit_interval(self, extractor: SatelliteFeatureExtractor) -> None:
        df = extractor.create_timeseries("AAPL", "2022-01-01/2022-06-30")
        assert (df >= 0.0).all().all() and (df <= 1.0).all().all()


class TestSupportedTickers:
    def test_returns_sorted_list(self, extractor: SatelliteFeatureExtractor) -> None:
        t = extractor.get_supported_tickers()
        assert isinstance(t, list) and t == sorted(t)

    def test_contains_known_tickers(self, extractor: SatelliteFeatureExtractor) -> None:
        t = extractor.get_supported_tickers()
        assert "AAPL" in t and "TSLA" in t


class TestSimulateOccupancy:
    def test_deterministic(self, extractor: SatelliteFeatureExtractor) -> None:
        r1 = extractor._simulate_occupancy("2022-01-01/2022-06-30")
        r2 = extractor._simulate_occupancy("2022-01-01/2022-06-30")
        pd.testing.assert_series_equal(r1, r2)

    def test_different_ranges_differ(
        self, extractor: SatelliteFeatureExtractor
    ) -> None:
        r1 = extractor._simulate_occupancy("2022-01-01/2022-06-30")
        r2 = extractor._simulate_occupancy("2021-01-01/2021-06-30")
        assert not r1.equals(r2)
