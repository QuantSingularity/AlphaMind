"""
## Tiingo API connector for financial data.

## This module provides a connector for accessing financial market data
## from Tiingo, including stock prices, fundamentals, and news.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Union

from market_data.connectors.base import (
    APIConnector,
    APICredentials,
    DataCategory,
    DataFormat,
    DataProvider,
    DataResponse,
    RateLimiter,
)


class TiingoConnector(APIConnector):
    """
    Connector for Tiingo API.

    This class provides methods for accessing financial market data
    from Tiingo, including stock prices, fundamentals, and news.

    Parameters
    ----------
    api_key : str
        Tiingo API key.
    """

    def __init__(self, api_key: str) -> None:
        credentials = APICredentials(api_key=api_key)
        base_url = "https://api.tiingo.com"
        rate_limiter = RateLimiter(requests_per_hour=500)
        super().__init__(
            credentials=credentials, base_url=base_url, rate_limiter=rate_limiter
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def provider_name(self) -> str:
        """
        Get the name of the data provider.

        Returns
        -------
        provider_name : str
            Name of the data provider.
        """
        return DataProvider.TIINGO.value

    def authenticate(self) -> bool:
        """
        Authenticate with the Tiingo API.

        Returns
        -------
        success : bool
            Whether authentication was successful.
        """
        response = self.get_ticker_metadata("AAPL")
        return response.is_success()

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare headers for API requests.

        Returns
        -------
        headers : dict
            Headers for API requests.
        """
        return {
            "Authorization": f"Token {self.credentials.api_key}",
            "Content-Type": "application/json",
        }

    def get_ticker_metadata(self, ticker: str) -> DataResponse:
        """
        Get metadata for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.

        Returns
        -------
        response : DataResponse
            Response containing the ticker metadata.
        """
        endpoint = f"tiingo/daily/{ticker}"
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_ticker_price(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        fmt: str = "json",
        resample_freq: Optional[str] = None,
    ) -> DataResponse:
        """
        Get historical price data for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "annually".
        fmt : str, default="json"
            Response format. Options: "json", "csv".
        resample_freq : str, optional
            Resample frequency. Options: "daily", "weekly", "monthly", "annually".

        Returns
        -------
        response : DataResponse
            Response containing the historical price data.
        """
        endpoint = f"tiingo/daily/{ticker}/prices"
        params: Dict[str, Any] = {}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        params["format"] = fmt
        params["frequency"] = frequency
        if resample_freq:
            params["resampleFreq"] = resample_freq
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_intraday_price(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        resample_freq: Optional[str] = None,
        after_hours: bool = True,
        fmt: str = "json",
    ) -> DataResponse:
        """
        Get intraday price data for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        resample_freq : str, optional
            Resample frequency. Options: "1min", "5min", "10min", "30min", "1hour".
        after_hours : bool, default=True
            Whether to include after-hours data.
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the intraday price data.
        """
        endpoint = f"iex/{ticker}"
        params: Dict[str, Any] = {}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S")
            params["endDate"] = end_date
        if resample_freq:
            params["resampleFreq"] = resample_freq
        params["format"] = fmt
        params["afterHours"] = str(after_hours).lower()
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_ticker_news(
        self,
        tickers: Union[str, List[str]],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        limit: int = 100,
        offset: int = 0,
        sort: str = "publishedDate",
    ) -> DataResponse:
        """
        Get news for tickers.

        Parameters
        ----------
        tickers : str or list
            Ticker symbol or list of ticker symbols.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        limit : int, default=100
            Number of results to return.
        offset : int, default=0
            Offset for pagination.
        sort : str, default="publishedDate"
            Field to sort by.

        Returns
        -------
        response : DataResponse
            Response containing the news.
        """
        endpoint = "tiingo/news"
        params = {"limit": limit, "offset": offset, "sortBy": sort}
        if isinstance(tickers, list):
            params["tickers"] = ",".join(tickers)
        else:
            params["tickers"] = tickers
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.NEWS,
            format=DataFormat.JSON,
        )

    def search_news(
        self,
        query: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        limit: int = 100,
        offset: int = 0,
        sort: str = "publishedDate",
    ) -> DataResponse:
        """
        Search for news.

        Parameters
        ----------
        query : str
            Search query.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        limit : int, default=100
            Number of results to return.
        offset : int, default=0
            Offset for pagination.
        sort : str, default="publishedDate"
            Field to sort by.

        Returns
        -------
        response : DataResponse
            Response containing the search results.
        """
        endpoint = "tiingo/news"
        params = {"query": query, "limit": limit, "offset": offset, "sortBy": sort}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.NEWS,
            format=DataFormat.JSON,
        )

    def get_fundamentals(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fmt: str = "json",
    ) -> DataResponse:
        """
        Get fundamentals data for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the fundamentals data.
        """
        endpoint = f"tiingo/fundamentals/{ticker}/statements"
        params = {"format": fmt}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_fundamentals_definitions(self, fmt: str = "json") -> DataResponse:
        """
        Get fundamentals definitions.

        Parameters
        ----------
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the fundamentals definitions.
        """
        endpoint = "tiingo/fundamentals/definitions"
        params = {"format": fmt}
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_fundamentals_metrics(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fmt: str = "json",
    ) -> DataResponse:
        """
        Get fundamentals metrics for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the fundamentals metrics.
        """
        endpoint = f"tiingo/fundamentals/{ticker}/daily"
        params = {"format": fmt}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_crypto_metadata(
        self, tickers: Optional[Union[str, List[str]]] = None
    ) -> DataResponse:
        """
        Get metadata for cryptocurrencies.

        Parameters
        ----------
        tickers : str or list, optional
            Ticker symbol or list of ticker symbols. If None, returns metadata for all cryptocurrencies.

        Returns
        -------
        response : DataResponse
            Response containing the cryptocurrency metadata.
        """
        endpoint = "tiingo/crypto"
        params: Dict[str, Any] = {}
        if tickers:
            if isinstance(tickers, list):
                params["tickers"] = ",".join(tickers)
            else:
                params["tickers"] = tickers
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_crypto_price(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        resample_freq: Optional[str] = None,
        base_currency: str = "USD",
        exchanges: Optional[Union[str, List[str]]] = None,
        consolidate: bool = True,
        crypto_price: str = "midPrice",
        fmt: str = "json",
    ) -> DataResponse:
        """
        Get historical price data for a cryptocurrency.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        resample_freq : str, optional
            Resample frequency. Options: "1min", "5min", "10min", "30min", "1hour", "4hour", "1day".
        base_currency : str, default="USD"
            Base currency.
        exchanges : str or list, optional
            Exchange or list of exchanges.
        consolidate : bool, default=True
            Whether to consolidate data from multiple exchanges.
        crypto_price : str, default="midPrice"
            Price type. Options: "midPrice", "bidPrice", "askPrice", "lastPrice".
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the historical price data.
        """
        endpoint = "tiingo/crypto/prices"
        params = {
            "tickers": ticker,
            "baseCurrency": base_currency,
            "priceType": crypto_price,
            "consolidate": str(consolidate).lower(),
            "format": fmt,
        }
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        if resample_freq:
            params["resampleFreq"] = resample_freq
        if exchanges:
            if isinstance(exchanges, list):
                params["exchanges"] = ",".join(exchanges)
            else:
                params["exchanges"] = exchanges
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_crypto_top_of_book(
        self,
        tickers: Union[str, List[str]],
        exchanges: Optional[Union[str, List[str]]] = None,
        include_price: bool = True,
        fmt: str = "json",
    ) -> DataResponse:
        """
        Get top of book data for cryptocurrencies.

        Parameters
        ----------
        tickers : str or list
            Ticker symbol or list of ticker symbols.
        exchanges : str or list, optional
            Exchange or list of exchanges.
        include_price : bool, default=True
            Whether to include price data.
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the top of book data.
        """
        endpoint = "tiingo/crypto/top"
        params = {"includePrice": str(include_price).lower(), "format": fmt}
        if isinstance(tickers, list):
            params["tickers"] = ",".join(tickers)
        else:
            params["tickers"] = tickers
        if exchanges:
            if isinstance(exchanges, list):
                params["exchanges"] = ",".join(exchanges)
            else:
                params["exchanges"] = exchanges
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_forex_metadata(
        self, tickers: Optional[Union[str, List[str]]] = None
    ) -> DataResponse:
        """
        Get metadata for forex pairs.

        Parameters
        ----------
        tickers : str or list, optional
            Ticker symbol or list of ticker symbols. If None, returns metadata for all forex pairs.

        Returns
        -------
        response : DataResponse
            Response containing the forex metadata.
        """
        endpoint = "tiingo/fx"
        params: Dict[str, Any] = {}
        if tickers:
            if isinstance(tickers, list):
                params["tickers"] = ",".join(tickers)
            else:
                params["tickers"] = tickers
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_forex_price(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        resample_freq: Optional[str] = None,
        fmt: str = "json",
    ) -> DataResponse:
        """
        Get historical price data for a forex pair.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        resample_freq : str, optional
            Resample frequency. Options: "1min", "5min", "10min", "30min", "1hour", "4hour", "1day".
        fmt : str, default="json"
            Response format. Options: "json", "csv".

        Returns
        -------
        response : DataResponse
            Response containing the historical price data.
        """
        endpoint = f"tiingo/fx/{ticker}/prices"
        params = {"format": fmt}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["startDate"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["endDate"] = end_date
        if resample_freq:
            params["resampleFreq"] = resample_freq
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if fmt == "json" else DataFormat.CSV,
        )

    def get_supported_tickers(self, asset_type: str = "stock") -> DataResponse:
        """
        Get supported tickers.

        Parameters
        ----------
        asset_type : str, default="stock"
            Asset type. Options: "stock", "crypto", "fx".

        Returns
        -------
        response : DataResponse
            Response containing the supported tickers.
        """
        if asset_type == "stock":
            endpoint = "tiingo/utilities/supported/tickers"
        elif asset_type == "crypto":
            endpoint = "tiingo/crypto/supported/tickers"
        elif asset_type == "fx":
            endpoint = "tiingo/fx/supported/pairs"
        else:
            raise ValueError(f"Invalid asset type: {asset_type}")
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_supported_exchanges(self, asset_type: str = "crypto") -> DataResponse:
        """
        Get supported exchanges.

        Parameters
        ----------
        asset_type : str, default="crypto"
            Asset type. Options: "crypto".

        Returns
        -------
        response : DataResponse
            Response containing the supported exchanges.
        """
        if asset_type == "crypto":
            endpoint = "tiingo/crypto/supported/exchanges"
        else:
            raise ValueError(f"Invalid asset type: {asset_type}")
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_supported_markets(self) -> DataResponse:
        """
        Get supported markets.

        Returns
        -------
        response : DataResponse
            Response containing the supported markets.
        """
        endpoint = "tiingo/utilities/supported/markets"
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )
