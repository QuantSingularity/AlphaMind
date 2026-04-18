""""""

""
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Union

import pandas as pd
from market_data.connectors.base import (
    APIConnector,
    APICredentials,
    DataCategory,
    DataFormat,
    DataProvider,
    DataResponse,
    RateLimiter,
)


class QuandlConnector(APIConnector):
    """"""

    ""

    def __init__(self, api_key: str) -> None:
        credentials = APICredentials(api_key=api_key)
        base_url = "https://www.quandl.com/api/v3"
        rate_limiter = RateLimiter(requests_per_second=30)
        super().__init__(
            credentials=credentials, base_url=base_url, rate_limiter=rate_limiter
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def provider_name(self) -> str:
        """"""
        ""
        return DataProvider.QUANDL.value

    def authenticate(self) -> bool:
        """"""
        ""
        response = self.get_dataset("WIKI/AAPL", rows=1)
        return response.is_success()

    def _add_api_key(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """"""
        ""
        params = params or {}
        params["api_key"] = self.credentials.api_key
        return params

    def get_dataset(
        self,
        dataset_code: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        column_index: Optional[Union[int, List[int]]] = None,
        collapse: Optional[str] = None,
        transform: Optional[str] = None,
        order: str = "asc",
        rows: Optional[int] = None,
        format: str = "json",
    ) -> DataResponse:
        """"""
        ""
        endpoint = f"datasets/{dataset_code}.{format}"
        params = self._add_api_key({"order": order})
        if start_date:
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y-%m-%d")
            params["start_date"] = start_date
        if end_date:
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date
        if column_index is not None:
            if isinstance(column_index, list):
                params["column_index"] = ",".join(map(str, column_index))
            else:
                params["column_index"] = str(column_index)
        if collapse:
            params["collapse"] = collapse
        if transform:
            params["transform"] = transform
        if rows:
            params["rows"] = rows
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=(
                DataFormat.JSON
                if format == "json"
                else DataFormat.CSV if format == "csv" else DataFormat.XML
            ),
        )

    def get_dataset_metadata(self, dataset_code: str) -> DataResponse:
        """"""
        ""
        endpoint = f"datasets/{dataset_code}/metadata"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_database_metadata(self, database_code: str) -> DataResponse:
        """"""
        ""
        endpoint = f"databases/{database_code}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def search_datasets(
        self,
        query: str,
        database_code: Optional[str] = None,
        per_page: int = 100,
        page: int = 1,
    ) -> DataResponse:
        """"""
        ""
        endpoint = "datasets"
        params = self._add_api_key({"query": query, "per_page": per_page, "page": page})
        if database_code:
            params["database_code"] = database_code
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def list_databases(self, per_page: int = 100, page: int = 1) -> DataResponse:
        """"""
        ""
        endpoint = "databases"
        params = self._add_api_key({"per_page": per_page, "page": page})
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON,
        )

    def get_datatable(self, datatable_code: str, format: str = "json") -> DataResponse:
        """"""
        ""
        endpoint = f"datatables/{datatable_code}.{format}"
        params = self._add_api_key()
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if format == "json" else DataFormat.CSV,
        )

    def get_datatable_with_filters(
        self, datatable_code: str, filters: Dict[str, Any], format: str = "json"
    ) -> DataResponse:
        """"""
        ""
        endpoint = f"datatables/{datatable_code}.{format}"
        params = self._add_api_key()
        for key, value in filters.items():
            if isinstance(value, list):
                params[key] = ",".join(map(str, value))
            else:
                params[key] = value
        return self.request(
            endpoint=endpoint,
            params=params,
            category=DataCategory.MARKET_DATA,
            format=DataFormat.JSON if format == "json" else DataFormat.CSV,
        )

    def get_time_series(
        self,
        database_code: str,
        dataset_code: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        collapse: Optional[str] = None,
        transform: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """"""
        ""
        dataset_code_full = f"{database_code}/{dataset_code}"
        response = self.get_dataset(
            dataset_code=dataset_code_full,
            start_date=start_date,
            end_date=end_date,
            collapse=collapse,
            transform=transform,
            rows=limit,
        )
        if not response.is_success():
            self.logger.error(f"Failed to get time series data: {response.error}")
            return pd.DataFrame()
        dataset = response.data.get("dataset", {})
        data = dataset.get("data", [])
        column_names = dataset.get("column_names", [])
        df = pd.DataFrame(data, columns=column_names)
        if len(column_names) > 0 and column_names[0].lower() == "date":
            df[column_names[0]] = pd.to_datetime(df[column_names[0]])
        return df

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        collapse: Optional[str] = None,
    ) -> pd.DataFrame:
        """"""
        ""
        try:
            df = self.get_time_series(
                database_code="WIKI",
                dataset_code=ticker,
                start_date=start_date,
                end_date=end_date,
                collapse=collapse,
            )
            if not df.empty:
                return df
        except Exception as e:
            self.logger.warning(f"Failed to get stock data from WIKI database: {e}")
        try:
            df = self.get_time_series(
                database_code="EOD",
                dataset_code=ticker,
                start_date=start_date,
                end_date=end_date,
                collapse=collapse,
            )
            if not df.empty:
                return df
        except Exception as e:
            self.logger.warning(f"Failed to get stock data from EOD database: {e}")
        try:
            df = self.get_time_series(
                database_code="EURONEXT",
                dataset_code=ticker,
                start_date=start_date,
                end_date=end_date,
                collapse=collapse,
            )
            if not df.empty:
                return df
        except Exception as e:
            self.logger.warning(f"Failed to get stock data from EURONEXT database: {e}")
        self.logger.error(f"Failed to get stock data for {ticker}")
        return pd.DataFrame()

    def get_economic_data(
        self,
        indicator_code: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
    ) -> pd.DataFrame:
        """"""
        ""
        response = self.get_dataset(
            dataset_code=indicator_code, start_date=start_date, end_date=end_date
        )
        if not response.is_success():
            self.logger.error(f"Failed to get economic data: {response.error}")
            return pd.DataFrame()
        dataset = response.data.get("dataset", {})
        data = dataset.get("data", [])
        column_names = dataset.get("column_names", [])
        df = pd.DataFrame(data, columns=column_names)
        if len(column_names) > 0 and column_names[0].lower() == "date":
            df[column_names[0]] = pd.to_datetime(df[column_names[0]])
        return df

    def get_futures_data(
        self,
        symbol: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
    ) -> pd.DataFrame:
        """"""
        ""
        response = self.get_dataset(
            dataset_code=symbol, start_date=start_date, end_date=end_date
        )
        if not response.is_success():
            self.logger.error(f"Failed to get futures data: {response.error}")
            return pd.DataFrame()
        dataset = response.data.get("dataset", {})
        data = dataset.get("data", [])
        column_names = dataset.get("column_names", [])
        df = pd.DataFrame(data, columns=column_names)
        if len(column_names) > 0 and column_names[0].lower() == "date":
            df[column_names[0]] = pd.to_datetime(df[column_names[0]])
        return df

    def get_forex_data(
        self,
        currency_pair: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
    ) -> pd.DataFrame:
        """"""
        ""
        try:
            dataset_code = f"CURRFX/{currency_pair}"
            response = self.get_dataset(
                dataset_code=dataset_code, start_date=start_date, end_date=end_date
            )
            if response.is_success():
                dataset = response.data.get("dataset", {})
                data = dataset.get("data", [])
                column_names = dataset.get("column_names", [])
                df = pd.DataFrame(data, columns=column_names)
                if len(column_names) > 0 and column_names[0].lower() == "date":
                    df[column_names[0]] = pd.to_datetime(df[column_names[0]])
                return df
        except Exception as e:
            self.logger.warning(f"Failed to get forex data from CURRFX database: {e}")
        self.logger.error(f"Failed to get forex data for {currency_pair}")
        return pd.DataFrame()

    def get_commodity_data(
        self,
        commodity_code: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
    ) -> pd.DataFrame:
        """"""
        ""
        response = self.get_dataset(
            dataset_code=commodity_code, start_date=start_date, end_date=end_date
        )
        if not response.is_success():
            self.logger.error(f"Failed to get commodity data: {response.error}")
            return pd.DataFrame()
        dataset = response.data.get("dataset", {})
        data = dataset.get("data", [])
        column_names = dataset.get("column_names", [])
        df = pd.DataFrame(data, columns=column_names)
        if len(column_names) > 0 and column_names[0].lower() == "date":
            df[column_names[0]] = pd.to_datetime(df[column_names[0]])
        return df
