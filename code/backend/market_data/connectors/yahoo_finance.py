"""
## Yahoo Finance API connector for financial data.

## This module provides a connector for accessing financial market data
## from Yahoo Finance, including stock prices, historical data,
## company information, and more.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import requests
from market_data.connectors.base import (
    APIConnector,
    APICredentials,
    DataCategory,
    DataFormat,
    DataProvider,
    DataRequest,
    DataResponse,
    RateLimiter,
)


class YahooFinanceConnector(APIConnector):
    """
    Connector for Yahoo Finance API.

    This class provides methods for accessing financial market data
    from Yahoo Finance, including stock prices, historical data,
    company information, and more.

    Parameters
    ----------
    rapid_api_key : str, optional
        RapidAPI key for accessing Yahoo Finance API.
        If None, uses the unofficial API.
    """

    def __init__(self, rapid_api_key: Optional[str] = None) -> None:
        credentials = APICredentials(api_key=rapid_api_key)
        if rapid_api_key:
            base_url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com"
            rate_limiter = RateLimiter(max_requests=60, time_window=60)
        else:
            base_url = "https://query1.finance.yahoo.com"
            rate_limiter = RateLimiter(requests_per_minute=100)
        super().__init__(
            credentials=credentials, base_url=base_url, rate_limiter=rate_limiter
        )
        self.using_rapid_api = rapid_api_key is not None
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
        return DataProvider.YAHOO_FINANCE.value

    def authenticate(self) -> bool:
        """
        Authenticate with the Yahoo Finance API.

        Returns
        -------
        success : bool
            Whether authentication was successful.
        """
        response = self.get_quote("AAPL")
        return response.is_success()

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare headers for API requests.

        Returns
        -------
        headers : dict
            Headers for API requests.
        """
        if self.using_rapid_api:
            return {
                "X-RapidAPI-Key": self.credentials.api_key,
                "X-RapidAPI-Host": "apidojo-yahoo-finance-v1.p.rapidapi.com",
            }
        else:
            return {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

    def get_quote(self, symbol: str) -> DataResponse:
        """
        Get real-time stock quote.

        Parameters
        ----------
        symbol : str
            Stock symbol.

        Returns
        -------
        response : DataResponse
            Response containing the stock quote.
        """
        if self.using_rapid_api:
            endpoint = "/market/v2/get-quotes"
            params = {"symbols": symbol, "region": "US"}
        else:
            endpoint = "/v7/finance/quote"
            params.update({"symbols": symbol})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_historical_data(
        self,
        symbol: str,
        period1: Optional[Union[datetime, str]] = None,
        period2: Optional[Union[datetime, str]] = None,
        interval: str = "1d",
        include_prepost: bool = False,
        events: str = "history",
    ) -> DataResponse:
        """
        Get historical stock data.

        Parameters
        ----------
        symbol : str
            Stock symbol.
        period1 : datetime or str, optional
            Start date. If None, uses 1 year ago.
        period2 : datetime or str, optional
            End date. If None, uses current date.
        interval : str, default="1d"
            Data interval. Options: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo".
        include_prepost : bool, default=False
            Whether to include pre and post market data.
        events : str, default="history"
            Events to include. Options: "history", "div", "split", "capitalGain".

        Returns
        -------
        response : DataResponse
            Response containing the historical data.
        """
        if period1 is None:
            period1 = datetime.now() - timedelta(days=365)
        if period2 is None:
            period2 = datetime.now()
        if isinstance(period1, str):
            period1 = datetime.fromisoformat(period1)
        if isinstance(period2, str):
            period2 = datetime.fromisoformat(period2)
        period1_timestamp = int(period1.timestamp())
        period2_timestamp = int(period2.timestamp())
        if self.using_rapid_api:
            endpoint = "/stock/v3/get-historical-data"
            params = {"symbol": symbol, "region": "US"}
        else:
            endpoint = "/v8/finance/chart/" + symbol
            params.update(
                {
                    "period1": period1_timestamp,
                    "period2": period2_timestamp,
                    "interval": interval,
                    "includePrePost": str(include_prepost).lower(),
                    "events": events,
                }
            )
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_options_chain(
        self, symbol: str, date: Optional[Union[datetime, str]] = None
    ) -> DataResponse:
        """
        Get options chain data.

        Parameters
        ----------
        symbol : str
            Stock symbol.
        date : datetime or str, optional
            Expiration date. If None, uses the nearest expiration date.

        Returns
        -------
        response : DataResponse
            Response containing the options chain data.
        """
        if self.using_rapid_api:
            endpoint = "/market/v2/get-options"
            params = {"symbol": symbol, "region": "US"}
            if date is not None:
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                params["date"] = date.strftime("%Y-%m-%d")
        else:
            endpoint = "/v7/finance/options/" + symbol
            params: Dict[str, Any] = {}
            if date is not None:
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                params["date"] = int(date.timestamp())
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_company_info(self, symbol: str) -> DataResponse:
        """
        Get company information.

        Parameters
        ----------
        symbol : str
            Stock symbol.

        Returns
        -------
        response : DataResponse
            Response containing the company information.
        """
        if self.using_rapid_api:
            endpoint = "/stock/v2/get-profile"
            params = {"symbol": symbol, "region": "US"}
        else:
            endpoint = "/v11/finance/quoteSummary/" + symbol
            params.update(
                {
                    "modules": "assetProfile,summaryProfile,summaryDetail,esgScores,price,incomeStatementHistory,incomeStatementHistoryQuarterly,balanceSheetHistory,balanceSheetHistoryQuarterly,cashflowStatementHistory,cashflowStatementHistoryQuarterly,defaultKeyStatistics,financialData,calendarEvents,secFilings,recommendationTrend,upgradeDowngradeHistory,institutionOwnership,fundOwnership,majorDirectHolders,majorHoldersBreakdown,insiderTransactions,insiderHolders,netSharePurchaseActivity,earnings,earningsHistory,earningsTrend,industryTrend,indexTrend,sectorTrend"
                }
            )
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_financial_statements(
        self, symbol: str, statement_type: str = "income", frequency: str = "annual"
    ) -> DataResponse:
        """
        Get financial statements.

        Parameters
        ----------
        symbol : str
            Stock symbol.
        statement_type : str, default="income"
            Type of statement. Options: "income", "balance", "cash".
        frequency : str, default="annual"
            Frequency of statements. Options: "annual", "quarterly".

        Returns
        -------
        response : DataResponse
            Response containing the financial statements.
        """
        if self.using_rapid_api:
            if statement_type == "income":
                endpoint = "/stock/v2/get-financials"
            elif statement_type == "balance":
                endpoint = "/stock/v2/get-balance-sheet"
            elif statement_type == "cash":
                endpoint = "/stock/v2/get-cash-flow"
            else:
                raise ValueError(f"Invalid statement type: {statement_type}")
            params = {"symbol": symbol, "region": "US"}
        else:
            endpoint = "/v11/finance/quoteSummary/" + symbol
            if statement_type == "income":
                module = (
                    "incomeStatementHistory"
                    if frequency == "annual"
                    else "incomeStatementHistoryQuarterly"
                )
            elif statement_type == "balance":
                module = (
                    "balanceSheetHistory"
                    if frequency == "annual"
                    else "balanceSheetHistoryQuarterly"
                )
            elif statement_type == "cash":
                module = (
                    "cashflowStatementHistory"
                    if frequency == "annual"
                    else "cashflowStatementHistoryQuarterly"
                )
            else:
                raise ValueError(f"Invalid statement type: {statement_type}")
            params.update({"modules": module})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_recommendations(self, symbol: str) -> DataResponse:
        """
        Get analyst recommendations.

        Parameters
        ----------
        symbol : str
            Stock symbol.

        Returns
        -------
        response : DataResponse
            Response containing the analyst recommendations.
        """
        if self.using_rapid_api:
            endpoint = "/stock/v2/get-recommendations"
            params = {"symbol": symbol, "region": "US"}
        else:
            endpoint = "/v11/finance/quoteSummary/" + symbol
            params.update({"modules": "recommendationTrend,upgradeDowngradeHistory"})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_earnings(self, symbol: str) -> DataResponse:
        """
        Get earnings data.

        Parameters
        ----------
        symbol : str
            Stock symbol.

        Returns
        -------
        response : DataResponse
            Response containing the earnings data.
        """
        if self.using_rapid_api:
            endpoint = "/stock/v2/get-earnings"
            params = {"symbol": symbol, "region": "US"}
        else:
            endpoint = "/v11/finance/quoteSummary/" + symbol
            params.update({"modules": "earnings,earningsHistory,earningsTrend"})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def search(
        self,
        query: str,
        quote_count: int = 6,
        news_count: int = 4,
        enable_fuzzy_query: bool = False,
        quote_type_filter: Optional[List[str]] = None,
    ) -> DataResponse:
        """
        Search for symbols, companies, ETFs, mutual funds, etc.

        Parameters
        ----------
        query : str
            Search query.
        quote_count : int, default=6
            Number of quotes to return.
        news_count : int, default=4
            Number of news items to return.
        enable_fuzzy_query : bool, default=False
            Whether to enable fuzzy matching.
        quote_type_filter : list, optional
            Filter by quote type. Options: "equity", "etf", "mutualfund", "index", "future", "option", "currency", "cryptocurrency".

        Returns
        -------
        response : DataResponse
            Response containing the search results.
        """
        if self.using_rapid_api:
            endpoint = "/auto-complete"
            params = {"q": query, "region": "US"}
        else:
            endpoint = "/v1/finance/search"
            params.update(
                {
                    "q": query,
                    "quotesCount": quote_count,
                    "newsCount": news_count,
                    "enableFuzzyQuery": str(enable_fuzzy_query).lower(),
                }
            )
            if quote_type_filter:
                params["quoteType"] = ",".join(quote_type_filter)
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_market_summary(self, region: str = "US") -> DataResponse:
        """
        Get market summary.

        Parameters
        ----------
        region : str, default="US"
            Region code.

        Returns
        -------
        response : DataResponse
            Response containing the market summary.
        """
        if self.using_rapid_api:
            endpoint = "/market/v2/get-summary"
            params = {"region": region}
        else:
            endpoint = "/v6/finance/quote/marketSummary"
            params.update({"lang": "en", "region": region})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_trending(self, region: str = "US") -> DataResponse:
        """
        Get trending stocks.

        Parameters
        ----------
        region : str, default="US"
            Region code.

        Returns
        -------
        response : DataResponse
            Response containing the trending stocks.
        """
        if self.using_rapid_api:
            endpoint = "/market/get-trending-tickers"
            params = {"region": region}
        else:
            endpoint = "/v1/finance/trending/" + region
            params: Dict[str, Any] = {}
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_news(
        self, category: str = "generalnews", region: str = "US"
    ) -> DataResponse:
        """
        Get financial news.

        Parameters
        ----------
        category : str, default="generalnews"
            News category.
        region : str, default="US"
            Region code.

        Returns
        -------
        response : DataResponse
            Response containing the financial news.
        """
        if self.using_rapid_api:
            endpoint = "/news/v2/list"
            params = {"region": region, "category": category}
        else:
            endpoint = "/v2/finance/news"
            params.update({"category": category, "region": region})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.NEWS,
            format=DataFormat.JSON,
        )

    def get_chart_data(
        self, symbol: str, interval: str = "1d", range: str = "1mo"
    ) -> DataResponse:
        """
        Get chart data.

        Parameters
        ----------
        symbol : str
            Stock symbol.
        interval : str, default="1d"
            Data interval. Options: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo".
        range : str, default="1mo"
            Data range. Options: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max".

        Returns
        -------
        response : DataResponse
            Response containing the chart data.
        """
        if self.using_rapid_api:
            endpoint = "/market/get-charts"
            params = {
                "symbol": symbol,
                "interval": interval,
                "range": range,
                "region": "US",
            }
        else:
            endpoint = "/v8/finance/chart/" + symbol
            params.update({"interval": interval, "range": range})
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_insights(self, symbol: str) -> DataResponse:
        """
        Get insights for a symbol.

        Parameters
        ----------
        symbol : str
            Stock symbol.

        Returns
        -------
        response : DataResponse
            Response containing the insights.
        """
        if self.using_rapid_api:
            endpoint = "/stock/v2/get-insights"
            params = {"symbol": symbol, "region": "US"}
        else:
            request = DataRequest(
                provider=self.provider_name,
                endpoint="/v2/finance/insights",
                method="GET",
                params={"symbol": symbol},
                headers=self._prepare_headers(),
                category=DataCategory.MARKET_DATA,
                format=DataFormat.JSON,
            )
            try:
                url = f"https://query1.finance.yahoo.com/ws/insights/v2/finance/insights?symbol={symbol}"
                response = requests.get(url, headers=self._prepare_headers())
                if response.status_code == 200:
                    return DataResponse(
                        request=request,
                        status_code=response.status_code,
                        data=response.json(),
                        headers=dict(response.headers),
                    )
                else:
                    return DataResponse(
                        request=request,
                        status_code=response.status_code,
                        data=None,
                        error=f"Failed to get insights: {response.text}",
                    )
            except Exception as e:
                return DataResponse(
                    request=request, status_code=500, data=None, error=str(e)
                )
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )
