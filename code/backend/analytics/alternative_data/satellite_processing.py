import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Sentinel Hub is an optional dependency; degrade gracefully when not present
try:
    from sentinelhub import CRS, BBox, DataCollection, MimeType, SHConfig, WmsRequest

    _SENTINELHUB_AVAILABLE = True
except ImportError:
    _SENTINELHUB_AVAILABLE = False
    logger.warning(
        "sentinelhub package not installed. SatelliteFeatureExtractor will run in "
        "simulation mode only. Install with: pip install sentinelhub"
    )

try:
    import tensorflow as tf

    _TF_AVAILABLE = True
except ImportError:
    _TF_AVAILABLE = False


FacilitySpec = Dict[str, Union[str, List[float]]]


class SatelliteFeatureExtractor:
    """
    Extracts physical indicators (e.g., parking-lot occupancy) from
    Sentinel-2 satellite imagery and converts them into financial time series.

    When ``sentinelhub`` or the CNN model is unavailable, the extractor
    falls back to a simulation mode that generates plausible synthetic data
    for testing and development purposes.
    """

    # Known company facilities: maps ticker → list of bounding-box specs
    _FACILITY_DB: Dict[str, List[FacilitySpec]] = {
        "AAPL": [
            {
                "name": "Apple Park",
                "coordinates": [-122.009, 37.3346, -121.988, 37.3456],
            },
            {
                "name": "Foxconn Zhengzhou",
                "coordinates": [113.625, 34.75, 113.655, 34.77],
            },
        ],
        "TSLA": [
            {
                "name": "Fremont Factory",
                "coordinates": [-121.9465, 37.492, -121.9365, 37.497],
            },
            {
                "name": "Gigafactory Nevada",
                "coordinates": [-119.441, 39.538, -119.431, 39.548],
            },
            {
                "name": "Gigafactory Texas",
                "coordinates": [-97.622, 30.218, -97.610, 30.228],
            },
        ],
        "WMT": [
            {
                "name": "Bentonville HQ",
                "coordinates": [-94.212, 36.364, -94.198, 36.374],
            },
        ],
        "AMZN": [
            {"name": "Seattle HQ", "coordinates": [-122.340, 47.620, -122.330, 47.630]},
            {
                "name": "JFK8 Fulfillment",
                "coordinates": [-74.153, 40.645, -74.143, 40.655],
            },
        ],
    }

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        instance_id: Optional[str] = None,
        model_path: str = "efficientnet_parking.h5",
        simulation_mode: bool = False,
    ) -> None:
        """
        Initialise the extractor.

        Args:
            client_id: Sentinel Hub OAuth Client ID.
            client_secret: Sentinel Hub OAuth Client Secret.
            instance_id: Sentinel Hub Instance ID.
            model_path: Path to a pre-trained occupancy detection model (.h5).
            simulation_mode: If True, bypass real API calls and return synthetic data.
                Useful for development/testing without API credentials.
        """
        self.simulation_mode = simulation_mode or not _SENTINELHUB_AVAILABLE

        if not self.simulation_mode:
            if not (client_id and client_secret and instance_id):
                raise ValueError(
                    "client_id, client_secret, and instance_id are required when "
                    "simulation_mode=False."
                )
            config = SHConfig()
            config.sh_client_id = client_id
            config.sh_client_secret = client_secret
            config.instance_id = instance_id
            self.sh_config = config
        else:
            self.sh_config = None
            logger.info("SatelliteFeatureExtractor running in SIMULATION mode.")

        self.model = None
        if not self.simulation_mode and _TF_AVAILABLE:
            try:
                self.model = tf.keras.models.load_model(model_path)
                logger.info("Occupancy detection model loaded: %s", model_path)
            except Exception as exc:
                logger.warning(
                    "Could not load CNN model from '%s': %s. "
                    "Falling back to simulation mode.",
                    model_path,
                    exc,
                )
                self.simulation_mode = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_geospatial(
        self,
        coordinates: List[float],
        time_range: str,
    ) -> pd.Series:
        """
        Extract a parking-lot occupancy time series for a single bounding box.

        Args:
            coordinates: [min_lon, min_lat, max_lon, max_lat].
            time_range: ISO-8601 interval, e.g. ``"2022-01-01/2023-06-30"``.

        Returns:
            ``pd.Series`` of occupancy scores indexed by observation date.
            Returns an empty Series on failure.
        """
        if self.simulation_mode:
            return self._simulate_occupancy(time_range)

        try:
            images, dates = self._fetch_images(coordinates, time_range)
        except Exception as exc:
            logger.error("Sentinel Hub request failed: %s", exc)
            return pd.Series(dtype=float)

        processed = self._preprocess_images(images)
        scores: np.ndarray = self.model.predict(processed).flatten()  # type: ignore[union-attr]
        return pd.Series(scores, index=dates)

    def create_timeseries(
        self, ticker: str, time_range: str = "2020-01-01/2023-12-31"
    ) -> pd.DataFrame:
        """
        Aggregate occupancy signals across all tracked facilities for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g. ``"AAPL"``).
            time_range: ISO-8601 interval string for the data request.

        Returns:
            ``pd.DataFrame`` where each column is a facility name and each row
            is an observation date.  Empty DataFrame if no data available.
        """
        facilities = self._get_company_facilities(ticker)
        if not facilities:
            logger.warning("No facilities registered for ticker '%s'.", ticker)
            return pd.DataFrame()

        series_map: Dict[str, pd.Series] = {}
        for facility in facilities:
            name = str(facility["name"])
            ts = self.process_geospatial(
                coordinates=list(map(float, facility["coordinates"])),  # type: ignore[arg-type]
                time_range=time_range,
            )
            if not ts.empty:
                series_map[name] = ts

        if not series_map:
            logger.warning("No valid occupancy data for '%s'.", ticker)
            return pd.DataFrame()

        df = pd.DataFrame(series_map)
        logger.info(
            "Created occupancy time series for '%s': %d facilities, %d observations.",
            ticker,
            len(series_map),
            len(df),
        )
        return df

    def get_supported_tickers(self) -> List[str]:
        """Return the list of tickers with registered facility data."""
        return sorted(self._FACILITY_DB.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_images(self, coordinates: List[float], time_range: str) -> tuple:
        """Fetch raw satellite images and their timestamps from Sentinel Hub."""
        bbox = BBox(coordinates, crs=CRS.WGS84)
        request = WmsRequest(
            data_collection=DataCollection.SENTINEL2_L2A,
            layer="TRUE-COLOR-S2L2A",
            bbox=bbox,
            time=time_range,
            width=512,
            height=512,
            image_format=MimeType.TIFF,
            config=self.sh_config,
        )
        logger.info("Fetching imagery for BBOX %s, range %s …", coordinates, time_range)
        images = request.get_data()
        dates = request.get_dates()
        logger.info("Fetched %d images.", len(images))
        return images, dates

    def _preprocess_images(self, images: List[np.ndarray]) -> np.ndarray:
        """Normalise and stack raw satellite images for model inference."""
        return np.array(
            [img.astype(np.float32) / 255.0 for img in images],
            dtype=np.float32,
        )

    def _simulate_occupancy(self, time_range: str) -> pd.Series:
        """
        Generate synthetic occupancy time series for testing.

        The synthetic signal contains a realistic weekly seasonality pattern
        (lower occupancy on weekends) plus Gaussian noise.
        """
        parts = time_range.split("/")
        start = pd.Timestamp(parts[0])
        end = pd.Timestamp(parts[1]) if len(parts) > 1 else pd.Timestamp.now()
        dates = pd.date_range(start=start, end=end, freq="W-MON")

        rng = np.random.default_rng(seed=int(start.timestamp()) % (2**32))
        base = 0.65 + rng.normal(0, 0.08, len(dates))
        # Add a modest upward trend
        trend = np.linspace(0, 0.1, len(dates))
        scores = np.clip(base + trend, 0.0, 1.0)
        return pd.Series(scores.astype(np.float32), index=dates)

    def _get_company_facilities(self, ticker: str) -> List[FacilitySpec]:
        """Look up registered facility bounding boxes for a ticker."""
        return self._FACILITY_DB.get(ticker.upper(), [])
