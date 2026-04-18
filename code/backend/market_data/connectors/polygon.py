"""
## Polygon.io API connector for financial data.

## This module provides a connector for accessing financial market data
## from Polygon.io, including stocks, options, forex, and crypto data.
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


class PolygonConnector(APIConnector):
    """
    Connector for Polygon.io API.

    This class provides methods for accessing financial market data
    from Polygon.io, including stocks, options, forex, and crypto data.

    Parameters
    ----------
    api_key : str
        Polygon.io API key.
    """

    def __init__(self, api_key: str) -> None:
        credentials = APICredentials(api_key=api_key)
        base_url = "https://api.polygon.io"
        rate_limiter = RateLimiter(requests_per_second=5)
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
        return DataProvider.POLYGON.value

    def authenticate(self) -> bool:
        """
        Authenticate with the Polygon.io API.

        Returns
        -------
        success : bool
            Whether authentication was successful.
        """
        response = self.get_ticker_details("AAPL")
        return response.is_success()

    def _add_api_key(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add API key to request parameters.

        Parameters
        ----------
        params : dict, optional
            Request parameters.

        Returns
        -------
        params : dict
            Request parameters with API key added.
        """
        params = params or {}
        params["apiKey"] = self.credentials.api_key
        return params

    def get_ticker_details(self, ticker: str) -> DataResponse:
        """
        Get details for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.

        Returns
        -------
        response : DataResponse
            Response containing the ticker details.
        """
        endpoint = f"v3/reference/tickers/{ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_tickers(
        self,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        type: Optional[str] = None,
        active: Optional[bool] = None,
        sort: str = "ticker",
        order: str = "asc",
        limit: int = 100,
        ticker_gte: Optional[str] = None,
        ticker_lte: Optional[str] = None,
    ) -> DataResponse:
        """
        Get tickers.

        Parameters
        ----------
        market : str, optional
            Market type. Options: "stocks", "crypto", "fx", "otc", "indices".
        exchange : str, optional
            Exchange code.
        type : str, optional
            Ticker type. Options: "CS", "ADRC", "ADRP", "ADRR", "UNIT", "RIGHT", "PFD", "FUND", "SP", "WARRANT", "INDEX", "ETF", "ETN".
        active : bool, optional
            Whether the ticker is active.
        sort : str, default="ticker"
            Field to sort by.
        order : str, default="asc"
            Sort order. Options: "asc", "desc".
        limit : int, default=100
            Number of results to return.
        ticker_gte : str, optional
            Ticker greater than or equal to.
        ticker_lte : str, optional
            Ticker less than or equal to.

        Returns
        -------
        response : DataResponse
            Response containing the tickers.
        """
        endpoint = "v3/reference/tickers"
        params = self._add_api_key({"sort": sort, "order": order, "limit": limit})
        if market:
            params["market"] = market
        if exchange:
            params["exchange"] = exchange
        if type:
            params["type"] = type
        if active is not None:
            params["active"] = str(active).lower()
        if ticker_gte:
            params["ticker.gte"] = ticker_gte
        if ticker_lte:
            params["ticker.lte"] = ticker_lte
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_ticker_news(
        self,
        ticker: Optional[str] = None,
        limit: int = 100,
        order: str = "desc",
        sort: str = "published_utc",
        published_utc_gte: Optional[str] = None,
        published_utc_lte: Optional[str] = None,
    ) -> DataResponse:
        """
        Get news for a ticker.

        Parameters
        ----------
        ticker : str, optional
            Ticker symbol. If None, returns news for all tickers.
        limit : int, default=100
            Number of results to return.
        order : str, default="desc"
            Sort order. Options: "asc", "desc".
        sort : str, default="published_utc"
            Field to sort by.
        published_utc_gte : str, optional
            Published date greater than or equal to (format: YYYY-MM-DD).
        published_utc_lte : str, optional
            Published date less than or equal to (format: YYYY-MM-DD).

        Returns
        -------
        response : DataResponse
            Response containing the news.
        """
        if ticker:
            endpoint = f"v2/reference/news?ticker={ticker}"
        else:
            endpoint = "v2/reference/news"
        params = self._add_api_key({"limit": limit, "order": order, "sort": sort})
        if published_utc_gte:
            params["published_utc.gte"] = published_utc_gte
        if published_utc_lte:
            params["published_utc.lte"] = published_utc_lte
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.NEWS,
            format=DataFormat.JSON,
        )

    def get_ticker_types(self) -> DataResponse:
        """
        Get ticker types.

        Returns
        -------
        response : DataResponse
            Response containing the ticker types.
        """
        endpoint = "v3/reference/tickers/types"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_market_status(self) -> DataResponse:
        """
        Get market status.

        Returns
        -------
        response : DataResponse
            Response containing the market status.
        """
        endpoint = "v1/marketstatus/now"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_market_holidays(self) -> DataResponse:
        """
        Get market holidays.

        Returns
        -------
        response : DataResponse
            Response containing the market holidays.
        """
        endpoint = "v1/marketstatus/upcoming"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_stock_exchanges(self) -> DataResponse:
        """
        Get stock exchanges.

        Returns
        -------
        response : DataResponse
            Response containing the stock exchanges.
        """
        endpoint = "v3/reference/exchanges"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_conditions(self, asset_class: str = "stocks") -> DataResponse:
        """
        Get conditions.

        Parameters
        ----------
        asset_class : str, default="stocks"
            Asset class. Options: "stocks", "options", "forex", "crypto".

        Returns
        -------
        response : DataResponse
            Response containing the conditions.
        """
        endpoint = f"v3/reference/conditions?asset_class={asset_class}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_previous_close(self, ticker: str, adjusted: bool = True) -> DataResponse:
        """
        Get previous close for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        adjusted : bool, default=True
            Whether to return adjusted data.

        Returns
        -------
        response : DataResponse
            Response containing the previous close.
        """
        endpoint = f"v2/aggs/ticker/{ticker}/prev"
        params = self._add_api_key({"adjusted": str(adjusted).lower()})
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_aggregates(
        self,
        ticker: str,
        multiplier: int,
        timespan: str,
        from_date: Union[str, date, datetime],
        to_date: Union[str, date, datetime],
        adjusted: bool = True,
        sort: str = "asc",
        limit: int = 5000,
    ) -> DataResponse:
        """
        Get aggregates (bars) for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        multiplier : int
            Multiplier for the timespan.
        timespan : str
            Timespan. Options: "minute", "hour", "day", "week", "month", "quarter", "year".
        from_date : str or date or datetime
            From date (format: YYYY-MM-DD).
        to_date : str or date or datetime
            To date (format: YYYY-MM-DD).
        adjusted : bool, default=True
            Whether to return adjusted data.
        sort : str, default="asc"
            Sort order. Options: "asc", "desc".
        limit : int, default=5000
            Number of results to return.

        Returns
        -------
        response : DataResponse
            Response containing the aggregates.
        """
        if isinstance(from_date, (date, datetime)):
            from_date = from_date.strftime("%Y-%m-%d")
        if isinstance(to_date, (date, datetime)):
            to_date = to_date.strftime("%Y-%m-%d")
        endpoint = f"v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = self._add_api_key(
            {"adjusted": str(adjusted).lower(), "sort": sort, "limit": limit}
        )
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_grouped_daily(
        self,
        date: Union[str, date, datetime],
        adjusted: bool = True,
        include_otc: bool = False,
    ) -> DataResponse:
        """
        Get grouped daily data for all tickers.

        Parameters
        ----------
        date : str or date or datetime
            Date (format: YYYY-MM-DD).
        adjusted : bool, default=True
            Whether to return adjusted data.
        include_otc : bool, default=False
            Whether to include OTC securities.

        Returns
        -------
        response : DataResponse
            Response containing the grouped daily data.
        """
        if isinstance(date, (date, datetime)):
            date = date.strftime("%Y-%m-%d")
        endpoint = f"v2/aggs/grouped/locale/us/market/stocks/{date}"
        params = self._add_api_key(
            {"adjusted": str(adjusted).lower(), "include_otc": str(include_otc).lower()}
        )
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_daily_open_close(
        self, ticker: str, date: Union[str, date, datetime], adjusted: bool = True
    ) -> DataResponse:
        """
        Get daily open/close for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        date : str or date or datetime
            Date (format: YYYY-MM-DD).
        adjusted : bool, default=True
            Whether to return adjusted data.

        Returns
        -------
        response : DataResponse
            Response containing the daily open/close.
        """
        if isinstance(date, (date, datetime)):
            date = date.strftime("%Y-%m-%d")
        endpoint = f"v1/open-close/{ticker}/{date}"
        params = self._add_api_key({"adjusted": str(adjusted).lower()})
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_last_quote(self, ticker: str) -> DataResponse:
        """
        Get last quote for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.

        Returns
        -------
        response : DataResponse
            Response containing the last quote.
        """
        endpoint = f"v2/last/nbbo/{ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_last_trade(self, ticker: str) -> DataResponse:
        """
        Get last trade for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.

        Returns
        -------
        response : DataResponse
            Response containing the last trade.
        """
        endpoint = f"v2/last/trade/{ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_snapshot(self, ticker: str) -> DataResponse:
        """
        Get snapshot for a ticker.

        Parameters
        ----------
        ticker : str
            Ticker symbol.

        Returns
        -------
        response : DataResponse
            Response containing the snapshot.
        """
        endpoint = f"v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_snapshots(self, tickers: List[str]) -> DataResponse:
        """
        Get snapshots for multiple tickers.

        Parameters
        ----------
        tickers : list
            List of ticker symbols.

        Returns
        -------
        response : DataResponse
            Response containing the snapshots.
        """
        tickers_str = ",".join(tickers)
        endpoint = f"v2/snapshot/locale/us/markets/stocks/tickers?tickers={tickers_str}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_gainers_losers(
        self, direction: str = "gainers", limit: int = 20
    ) -> DataResponse:
        """
        Get gainers or losers.

        Parameters
        ----------
        direction : str, default="gainers"
            Direction. Options: "gainers", "losers".
        limit : int, default=20
            Number of results to return.

        Returns
        -------
        response : DataResponse
            Response containing the gainers or losers.
        """
        endpoint = f"v2/snapshot/locale/us/markets/stocks/{direction}"
        params = self._add_api_key({"limit": limit})
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_forex_currencies(self) -> DataResponse:
        """
        Get forex currencies.

        Returns
        -------
        response : DataResponse
            Response containing the forex currencies.
        """
        endpoint = "v3/reference/currencies"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_forex_last_quote(
        self, from_currency: str, to_currency: str
    ) -> DataResponse:
        """
        Get last forex quote.

        Parameters
        ----------
        from_currency : str
            From currency code.
        to_currency : str
            To currency code.

        Returns
        -------
        response : DataResponse
            Response containing the last forex quote.
        """
        ticker = f"C:{from_currency}{to_currency}"
        endpoint = f"v1/last_quote/currencies/{ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_crypto_last_trade(
        self, from_currency: str, to_currency: str
    ) -> DataResponse:
        """
        Get last crypto trade.

        Parameters
        ----------
        from_currency : str
            From currency code.
        to_currency : str
            To currency code.

        Returns
        -------
        response : DataResponse
            Response containing the last crypto trade.
        """
        ticker = f"X:{from_currency}{to_currency}"
        endpoint = f"v1/last/crypto/{ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_options_contracts(
        self,
        underlying_ticker: str,
        expiration_date: Optional[str] = None,
        contract_type: Optional[str] = None,
        strike_price: Optional[float] = None,
        limit: int = 100,
        sort: str = "expiration_date",
        order: str = "asc",
    ) -> DataResponse:
        """
        Get options contracts.

        Parameters
        ----------
        underlying_ticker : str
            Underlying ticker symbol.
        expiration_date : str, optional
            Expiration date (format: YYYY-MM-DD).
        contract_type : str, optional
            Contract type. Options: "call", "put".
        strike_price : float, optional
            Strike price.
        limit : int, default=100
            Number of results to return.
        sort : str, default="expiration_date"
            Field to sort by.
        order : str, default="asc"
            Sort order. Options: "asc", "desc".

        Returns
        -------
        response : DataResponse
            Response containing the options contracts.
        """
        endpoint = "v3/reference/options/contracts"
        params = self._add_api_key(
            {
                "underlying_ticker": underlying_ticker,
                "limit": limit,
                "sort": sort,
                "order": order,
            }
        )
        if expiration_date:
            params["expiration_date"] = expiration_date
        if contract_type:
            params["contract_type"] = contract_type
        if strike_price:
            params["strike_price"] = strike_price
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_options_last_trade(self, options_ticker: str) -> DataResponse:
        """
        Get last options trade.

        Parameters
        ----------
        options_ticker : str
            Options ticker symbol.

        Returns
        -------
        response : DataResponse
            Response containing the last options trade.
        """
        endpoint = f"v2/last/trade/{options_ticker}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_technical_indicators(
        self,
        ticker: str,
        indicator_type: str,
        timestamp: Optional[int] = None,
        timespan: str = "day",
        adjusted: bool = True,
        window: int = 14,
        series_type: str = "close",
        expand_underlying: bool = False,
        order: str = "desc",
        limit: int = 5000,
    ) -> DataResponse:
        """
        Get technical indicators.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        indicator_type : str
            Indicator type. Options: "sma", "ema", "macd", "rsi".
        timestamp : int, optional
            Timestamp in milliseconds.
        timespan : str, default="day"
            Timespan. Options: "minute", "hour", "day", "week", "month", "quarter", "year".
        adjusted : bool, default=True
            Whether to use adjusted data.
        window : int, default=14
            Window size.
        series_type : str, default="close"
            Series type. Options: "close", "open", "high", "low".
        expand_underlying : bool, default=False
            Whether to expand underlying data.
        order : str, default="desc"
            Sort order. Options: "asc", "desc".
        limit : int, default=5000
            Number of results to return.

        Returns
        -------
        response : DataResponse
            Response containing the technical indicators.
        """
        endpoint = f"v1/indicators/{indicator_type}/{ticker}"
        params = self._add_api_key(
            {
                "timespan": timespan,
                "adjusted": str(adjusted).lower(),
                "window": window,
                "series_type": series_type,
                "expand_underlying": str(expand_underlying).lower(),
                "order": order,
                "limit": limit,
            }
        )
        if timestamp:
            params["timestamp"] = timestamp
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )
