import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from market_data.connectors.base import (
    APIConnector,
    APICredentials,
    DataCategory,
    DataFormat,
    DataProvider,
    DataResponse,
    RateLimiter,
)


class IntrinioConnector(APIConnector):
    """
    Connector for Intrinio API.

    This class provides methods for accessing financial market data
    from Intrinio, including stock prices, fundamentals, and economic data.

    Parameters
    ----------
    api_key : str
        Intrinio API key.
    sandbox : bool, default=False
        Whether to use the sandbox environment.
    """

    def __init__(self, api_key: str, sandbox: bool = False) -> None:
        credentials = APICredentials(api_key=api_key)
        if sandbox:
            base_url = "https://sandbox-api.intrinio.com"
        else:
            base_url = "https://api-v2.intrinio.com"
        rate_limiter = RateLimiter(requests_per_minute=10)
        super().__init__(
            credentials=credentials, base_url=base_url, rate_limiter=rate_limiter
        )
        self.sandbox = sandbox
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
        return DataProvider.INTRINIO.value

    def authenticate(self) -> bool:
        """
        Authenticate with the Intrinio API.

        Returns
        -------
        success : bool
            Whether authentication was successful.
        """
        response = self.get_company("AAPL")
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
            "Authorization": f"Bearer {self.credentials.api_key}",
            "Accept": "application/json",
        }

    def get_company(self, identifier: str) -> DataResponse:
        """
        Get company information.

        Parameters
        ----------
        identifier : str
            Company identifier (ticker symbol, CIK, LEI, etc.).

        Returns
        -------
        response : DataResponse
            Response containing the company information.
        """
        endpoint = f"companies/{identifier}"
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_company_news(
        self, identifier: str, page_size: int = 100, next_page: Optional[str] = None
    ) -> DataResponse:
        """
        Get news for a company.

        Parameters
        ----------
        identifier : str
            Company identifier (ticker symbol, CIK, LEI, etc.).
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the company news.
        """
        endpoint = f"companies/{identifier}/news"
        params = {"page_size": page_size}
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.NEWS,
            format=DataFormat.JSON,
        )

    def get_company_fundamentals(
        self,
        identifier: str,
        statement: str = "income_statement",
        fiscal_period: str = "FY",
        fiscal_year: Optional[int] = None,
        reported_only: bool = False,
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get fundamentals for a company.

        Parameters
        ----------
        identifier : str
            Company identifier (ticker symbol, CIK, LEI, etc.).
        statement : str, default="income_statement"
            Financial statement. Options: "income_statement", "balance_sheet", "cash_flow_statement", "calculations".
        fiscal_period : str, default="FY"
            Fiscal period. Options: "FY" (fiscal year), "Q1", "Q2", "Q3", "Q4", "H1" (first half), "H2" (second half), "9M" (nine months), "TTM" (trailing twelve months).
        fiscal_year : int, optional
            Fiscal year.
        reported_only : bool, default=False
            Whether to include only reported fundamentals.
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the company fundamentals.
        """
        endpoint = f"companies/{identifier}/fundamentals"
        params = {
            "statement": statement,
            "fiscal_period": fiscal_period,
            "reported": str(reported_only).lower(),
            "page_size": page_size,
        }
        if fiscal_year:
            params["fiscal_year"] = fiscal_year
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_company_metrics(
        self,
        identifier: str,
        metrics: Optional[Union[str, List[str]]] = None,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get metrics for a company.

        Parameters
        ----------
        identifier : str
            Company identifier (ticker symbol, CIK, LEI, etc.).
        metrics : str or list, optional
            Metric or list of metrics.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "quarterly", "yearly".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the company metrics.
        """
        endpoint = f"companies/{identifier}/historical_data"
        params = {"frequency": frequency, "page_size": page_size}
        if metrics:
            if isinstance(metrics, list):
                params["metrics"] = ",".join(metrics)
            else:
                params["metrics"] = metrics
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_security_prices(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get historical prices for a security.

        Parameters
        ----------
        identifier : str
            Security identifier (ticker symbol, FIGI, ISIN, CUSIP, etc.).
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "quarterly", "yearly".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the historical prices.
        """
        endpoint = f"securities/{identifier}/prices"
        params = {"frequency": frequency, "page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_security_intraday_prices(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "1min",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get intraday prices for a security.

        Parameters
        ----------
        identifier : str
            Security identifier (ticker symbol, FIGI, ISIN, CUSIP, etc.).
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="1min"
            Data frequency. Options: "1min", "5min", "15min", "30min", "60min".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the intraday prices.
        """
        endpoint = f"securities/{identifier}/prices/intraday"
        params = {"frequency": frequency, "page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_security_realtime_price(
        self, identifier: str, source: Optional[str] = None
    ) -> DataResponse:
        """
        Get real-time price for a security.

        Parameters
        ----------
        identifier : str
            Security identifier (ticker symbol, FIGI, ISIN, CUSIP, etc.).
        source : str, optional
            Price source.

        Returns
        -------
        response : DataResponse
            Response containing the real-time price.
        """
        endpoint = f"securities/{identifier}/prices/realtime"
        params: Dict[str, Any] = {}
        if source:
            params["source"] = source
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_security_dividends(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get dividends for a security.

        Parameters
        ----------
        identifier : str
            Security identifier (ticker symbol, FIGI, ISIN, CUSIP, etc.).
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "quarterly", "yearly".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the dividends.
        """
        endpoint = f"securities/{identifier}/dividends"
        params = {"frequency": frequency, "page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_security_earnings(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get earnings for a security.

        Parameters
        ----------
        identifier : str
            Security identifier (ticker symbol, FIGI, ISIN, CUSIP, etc.).
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the earnings.
        """
        endpoint = f"securities/{identifier}/earnings"
        params = {"page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def get_economic_index(self, identifier: str) -> DataResponse:
        """
        Get economic index information.

        Parameters
        ----------
        identifier : str
            Economic index identifier.

        Returns
        -------
        response : DataResponse
            Response containing the economic index information.
        """
        endpoint = f"indices/economic/{identifier}"
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.ECONOMIC,
            format=DataFormat.JSON,
        )

    def get_economic_index_data(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get data for an economic index.

        Parameters
        ----------
        identifier : str
            Economic index identifier.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "quarterly", "yearly".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the economic index data.
        """
        endpoint = f"indices/economic/{identifier}/data"
        params = {"frequency": frequency, "page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.ECONOMIC,
            format=DataFormat.JSON,
        )

    def get_stock_market_index(self, identifier: str) -> DataResponse:
        """
        Get stock market index information.

        Parameters
        ----------
        identifier : str
            Stock market index identifier.

        Returns
        -------
        response : DataResponse
            Response containing the stock market index information.
        """
        endpoint = f"indices/stock_market/{identifier}"
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_stock_market_index_data(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get data for a stock market index.

        Parameters
        ----------
        identifier : str
            Stock market index identifier.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "quarterly", "yearly".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the stock market index data.
        """
        endpoint = f"indices/stock_market/{identifier}/data"
        params = {"frequency": frequency, "page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_forex_currency(self, pair: str) -> DataResponse:
        """
        Get forex currency pair information.

        Parameters
        ----------
        pair : str
            Forex currency pair.

        Returns
        -------
        response : DataResponse
            Response containing the forex currency pair information.
        """
        endpoint = f"forex/currencies/{pair}"
        return self.request(
            endpoint=endpoint,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_forex_currency_prices(
        self,
        pair: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        frequency: str = "daily",
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get prices for a forex currency pair.

        Parameters
        ----------
        pair : str
            Forex currency pair.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        frequency : str, default="daily"
            Data frequency. Options: "daily", "weekly", "monthly", "quarterly", "yearly".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the forex currency pair prices.
        """
        endpoint = f"forex/currencies/{pair}/prices"
        params = {"frequency": frequency, "page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[Union[str, date, datetime]] = None,
        strike: Optional[float] = None,
        type: Optional[str] = None,
        moneyness: Optional[str] = None,
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get options chain.

        Parameters
        ----------
        symbol : str
            Underlying symbol.
        expiration : str or date or datetime, optional
            Expiration date (format: YYYY-MM-DD).
        strike : float, optional
            Strike price.
        type : str, optional
            Option type. Options: "call", "put".
        moneyness : str, optional
            Moneyness. Options: "all", "in_the_money", "out_of_the_money", "near_the_money".
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the options chain.
        """
        endpoint = "options/chain"
        params = {"symbol": symbol, "page_size": page_size}
        if expiration:
            if isinstance(expiration, (date, datetime)):
                expiration = expiration.strftime("%Y-%m-%d")
            params["expiration"] = expiration
        if strike:
            params["strike"] = strike
        if type:
            params["type"] = type
        if moneyness:
            params["moneyness"] = moneyness
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_options_expirations(self, symbol: str) -> DataResponse:
        """
        Get options expirations.

        Parameters
        ----------
        symbol : str
            Underlying symbol.

        Returns
        -------
        response : DataResponse
            Response containing the options expirations.
        """
        endpoint = "options/expirations"
        params = {"symbol": symbol}
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_options_prices(
        self,
        identifier: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        page_size: int = 100,
        next_page: Optional[str] = None,
    ) -> DataResponse:
        """
        Get historical prices for an option.

        Parameters
        ----------
        identifier : str
            Option identifier.
        start_date : str or date or datetime, optional
            Start date (format: YYYY-MM-DD).
        end_date : str or date or datetime, optional
            End date (format: YYYY-MM-DD).
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the historical option prices.
        """
        endpoint = f"options/prices/{identifier}"
        params = {"page_size": page_size}
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def search_companies(
        self, query: str, page_size: int = 100, next_page: Optional[str] = None
    ) -> DataResponse:
        """
        Search for companies.

        Parameters
        ----------
        query : str
            Search query.
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the search results.
        """
        endpoint = "companies/search"
        params = {"query": query, "page_size": page_size}
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.FUNDAMENTAL,
            format=DataFormat.JSON,
        )

    def search_securities(
        self, query: str, page_size: int = 100, next_page: Optional[str] = None
    ) -> DataResponse:
        """
        Search for securities.

        Parameters
        ----------
        query : str
            Search query.
        page_size : int, default=100
            Number of results per page.
        next_page : str, optional
            Token for the next page of results.

        Returns
        -------
        response : DataResponse
            Response containing the search results.
        """
        endpoint = "securities/search"
        params = {"query": query, "page_size": page_size}
        if next_page:
            params["next_page"] = next_page
        return self.request(
            endpoint=endpoint,
            params=params,
            headers=self._prepare_headers(),
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )
