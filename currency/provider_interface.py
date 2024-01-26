import abc
import json
import os
from datetime import datetime
from decimal import Decimal

import requests


class ProviderError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FormalAdapterInterface(abc.ABC):
    @abc.abstractmethod
    def get_latest_rate(
        self, source_currency_code: str, exchanged_currency_code: str
    ) -> Decimal:
        raise NotImplementedError

    @abc.abstractmethod
    def get_historical_rates(
        self,
        source_currency_code: str,
        exchanged_currency_code: str,
        valuation_date: datetime,
    ) -> Decimal:
        raise NotImplementedError


class FileJsonAdapter(FormalAdapterInterface):
    """
    A class to represent a JSON adapter for a file.
    This class is a child of the FormalAdapterInterface.

    Attributes:
    ----------
    address : str
        The address of the file.
    access_key : str
        The access key for the file.
    latest_endpoint_path : str
        The path to the latest endpoint in the file.
    latest_endpoint_args : dict
        The arguments for the latest endpoint in the file.
    latest_response_path : str
        The path to the latest response in the file.
    historical_endpoint_path : str
        The path to the historical endpoint in the file.
    historical_endpoint_args : dict
        The arguments for the historical endpoint in the file.
    historical_response_path : str
        The path to the historical response in the file.

    Methods:
    -------
    get_latest_rate(
        self,
        source_currency_code: str,
        exchanged_currency_code: str
    ) -> Decimal | None:
        Returns the latest exchange rate for a given source
        and exchanged currency code.

    get_historical_rates(
        self,
        source_currency_code: str,
        valuation_date: datetime
        ) -> dict | None:
        Returns the historical exchange rates for a given source currency code
        and valuation date.
    """

    def __init__(self, address: str, provider_config: dict):
        self.address = address
        self.access_key = provider_config["auth"].get("access_key", "")
        self.latest_endpoint_path = provider_config["endpoints"]["latest"][
            "request"
        ]["path"]
        self.latest_endpoint_args = provider_config["endpoints"]["latest"][
            "request"
        ]
        self.latest_response_path = provider_config["endpoints"]["latest"][
            "response"
        ]["path"]
        self.historical_endpoint_path = provider_config["endpoints"][
            "historical"
        ]["request"]["path"]
        self.historical_endpoint_args = provider_config["endpoints"][
            "historical"
        ]
        self.historical_response_path = provider_config["endpoints"][
            "historical"
        ]["response"]["path"]

    def get_latest_rate(
        self, source_currency_code: str, exchanged_currency_code: str
    ) -> Decimal | None:
        """
        Returns the latest exchange rate between the source
        and exchange currencies.

        Parameters
        ----------
            source_currency_code : str
                The code of the source currency.
            exchanged_currency_code : str
                The code of the exchanged currency.

        Returns
        -------
        Decimal | None
            The latest exchange rate if exists, otherwise None.
        """
        file_path = os.path.join(self.address, self.latest_endpoint_path)
        with open(file_path, "r") as f:
            data = json.load(f)
        try:
            rates = next(
                item["rates"]
                for item in data
                if item["base"] == source_currency_code
            )
        except StopIteration:
            raise ProviderError("Source currency was not found in the file.")
        return Decimal(rates[exchanged_currency_code])

    def get_historical_rates(
        self,
        source_currency_code: str,
        exchanged_currency_code: str,
        valuation_date: datetime,
    ) -> dict | None:
        """
        Returns the historical exchange rates for a specific date
        between the source and exchange currencies.

        Parameters
        ----------
            source_currency_code : str
                The code of the source currency.
            exchanged_currency_code : str
                The code of the exchanged currency.
            valuation_date : datetime
                The date for which the historical exchange rates are needed.

        Returns
        -------
        dict | None
            The historical exchange rates if exists, otherwise None.
        """
        str_date = valuation_date.strftime("%Y-%m-%d")
        file_path = os.path.join(self.address, self.historical_endpoint_path)
        with open(file_path, "r") as f:
            response = json.load(f)
        try:
            date_rates = next(
                item
                for item in response
                if item["date"] == str_date
                and item["base"] == source_currency_code
            )
        except StopIteration:
            return None
        return date_rates


class HttpJsonAdapter(FormalAdapterInterface):
    """
    A class used to represent an HTTP JSON Adapter.

    ...

    Attributes
    ----------
    address : str
        The address of the HTTP provider.
    access_key : str
        The access key used for the HTTP provider.
    latest_endpoint_path : str
        The path used for the latest endpoint.
    latest_endpoint_args : str
        The arguments used for the latest endpoint.
    latest_response_path : str
        The path used for the latest response.
    historical_endpoint_path : str
        The path used for the historical endpoint.
    historical_endpoint_args : str
        The arguments used for the historical endpoint.
    historical_response_path : str
        The path used for the historical response.

    Methods
    -------
    get_latest_rate(
        self,
        source_currency_code: str,
        exchanged_currency_code: str
    ) -> Decimal | None:
        Returns the latest exchange rate between the source
        and exchange currencies.

    get_historical_rates(
        self,
        source_currency_code: str,
        exchanged_currency_code: str,
        valuation_date: datetime
    ) -> dict | None:
        Returns the historical exchange rates for a specific date
        between the source and exchange currencies.
    """

    def __init__(self, address: str, provider_config: dict):
        """
        Constructs an HTTP JSON Adapter object.

        Parameters
        ----------
            address : str
                The address of the HTTP provider.
            provider_config : dict
                Configuration of the HTTP provider including access key,
                endpoints and paths.
        """
        self.address = address
        self.access_key = provider_config["auth"]["access_key"]
        self.latest_endpoint_path = provider_config["endpoints"]["latest"][
            "request"
        ]["path"]
        self.latest_endpoint_args = provider_config["endpoints"]["latest"][
            "request"
        ]["args"]
        self.latest_response_path = provider_config["endpoints"]["latest"][
            "response"
        ]["path"]
        self.historical_endpoint_path = provider_config["endpoints"][
            "historical"
        ]["request"]["path"]
        self.historical_endpoint_args = provider_config["endpoints"][
            "historical"
        ]["request"]["args"]
        self.historical_response_path = provider_config["endpoints"][
            "historical"
        ]["response"]["path"]

    def get_latest_rate(
        self, source_currency_code: str, exchanged_currency_code: str
    ) -> Decimal | dict | None:
        """
        Returns the latest exchange rate between the source
        and exchange currencies.

        Parameters
        ----------
            source_currency_code : str
                The code of the source currency.
            exchanged_currency_code : str
                The code of the exchanged currency.

        Returns
        -------
        Decimal | None
            The latest exchange rate if exists, otherwise None.
        """
        url = "".join([self.address, self.latest_endpoint_path])
        payload = {
            "access_key": self.access_key,
            self.latest_endpoint_args[
                "source_currency_code"
            ]: source_currency_code,
            self.latest_endpoint_args[
                "exchanged_currency_code"
            ]: exchanged_currency_code,
        }
        r = requests.get(url, params=payload)
        response = r.json()
        rates = response.get(self.latest_response_path, None)
        if not rates:
            raise ProviderError("Provider did not return any rates.")
        if "," in exchanged_currency_code:
            return rates
        return Decimal(rates[exchanged_currency_code])

    def get_historical_rates(
        self,
        source_currency_code: str,
        exchanged_currency_code: str,
        valuation_date: datetime,
    ) -> dict | None:
        """
        Returns the historical exchange rates for a specific date
        between the source and exchange currencies.

        Parameters
        ----------
            source_currency_code : str
                The code of the source currency.
            exchanged_currency_code : str
                The code of the exchanged currency.
            valuation_date : datetime
                The date for which the historical exchange rates are needed.

        Returns
        -------
        dict | None
            The historical exchange rates if exists, otherwise None.
        """
        str_date = valuation_date.strftime("%Y-%m-%d")
        url = "".join(
            [
                self.address,
                self.historical_endpoint_path.replace("$date", str_date),
            ]
        )
        payload = {
            "access_key": self.access_key,
            self.historical_endpoint_args[
                "source_currency_code"
            ]: source_currency_code,
            self.historical_endpoint_args[
                "exchanged_currency_code"
            ]: exchanged_currency_code,
        }
        r = requests.get(url, params=payload)
        response = r.json()
        rates = response.get(self.historical_response_path, None)
        if not rates:
            raise ProviderError("Provider did not return any rates.")
        return rates
