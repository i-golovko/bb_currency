import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, mock_open, patch

from currency.provider_interface import (
    FileJsonAdapter,
    HttpJsonAdapter,
    ProviderError,
)


class FileJsonAdapterTest(unittest.TestCase):
    def setUp(self):
        address = "test_address"
        provider_config = {
            "auth": {"access_key": "test_key"},
            "endpoints": {
                "latest": {
                    "request": {"path": "test_latest_path"},
                    "response": {"path": "test_latest_response_path"},
                },
                "historical": {
                    "request": {"path": "test_historical_path"},
                    "response": {"path": "test_historical_response_path"},
                },
            },
        }
        self.adapter = FileJsonAdapter(address, provider_config)

    # address = "/fake/path"
    # fake_latest_file = "latest.json"
    # fake_historical_file = "historical.json"
    # config = {
    #     "auth": {},
    #     "endpoints": {
    #         "latest": {
    #             "request": {
    #                 "path": fake_latest_file,
    #                 "source_currency_code": "base",
    #                 "exchanged_currency_code": "symbols",
    #             },
    #             "response": {"path": "rates"},
    #         },
    #         "historical": {
    #             "request": {
    #                 "path": fake_historical_file,
    #                 "source_currency_code": "base",
    #                 "exchanged_currency_code": "symbols",
    #             },
    #             "response": {"path": "rates"},
    #         },
    #     },
    # }
    # latest_json_content = json.dumps(
    #     {
    #         "date": "2024-01-25",
    #         "base": "EUR",
    #         "rates": {"USD": 1.08907, "CHF": 0.941669, "GBP": 0.855518},
    #     }
    # # )

    # historical_json_content = json.dumps(
    #     [
    #         {
    #             "date": "2024-01-24",
    #             "base": "EUR",
    #             "rates": {"USD": 1.200486, "GBP": 1.040662, "CHF": 0.797766},
    #         },
    #         {
    #             "date": "2024-01-23",
    #             "base": "EUR",
    #             "rates": {"USD": 1.195722, "GBP": 1.01497, "CHF": 0.891424},
    #         },
    #     ]
    # )


class TestFileJsonAdapter(unittest.TestCase):
    def setUp(self):
        address = "test_address"
        provider_config = {
            "auth": {"access_key": "test_key"},
            "endpoints": {
                "latest": {
                    "request": {"path": "test_latest_path"},
                    "response": {"path": "test_latest_response_path"},
                },
                "historical": {
                    "request": {"path": "test_historical_path"},
                    "response": {"path": "test_historical_response_path"},
                },
            },
        }
        self.adapter = FileJsonAdapter(address, provider_config)

    @patch("json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_latest_rate(self, mock_open, mock_json_load):
        mock_json_load.return_value = [
            {"base": "USD", "rates": {"EUR": "0.85"}},
            {"base": "GBP", "rates": {"EUR": "1.15"}},
        ]
        result = self.adapter.get_latest_rate("GBP", "EUR")
        self.assertEqual(result, Decimal("1.15"))

    @patch("json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_latest_rate_not_found(self, mock_open, mock_json_load):
        mock_json_load.return_value = [
            {"base": "USD", "rates": {"EUR": "0.85"}},
            {"base": "GBP", "rates": {"EUR": "1.15"}},
        ]
        with self.assertRaises(ProviderError):
            self.adapter.get_latest_rate("JPY", "EUR")

    @patch("json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_historical_rates(self, mock_open, mock_json_load):
        mock_json_load.return_value = [
            {"date": "2022-01-01", "base": "USD", "rates": {"EUR": "0.85"}},
            {"date": "2022-01-02", "base": "GBP", "rates": {"EUR": "1.15"}},
        ]
        result = self.adapter.get_historical_rates(
            "GBP", "EUR", datetime(2022, 1, 2)
        )
        self.assertEqual(
            result,
            {"date": "2022-01-02", "base": "GBP", "rates": {"EUR": "1.15"}},
        )

    @patch("json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_historical_rates_not_found(self, mock_open, mock_json_load):
        mock_json_load.return_value = [
            {"date": "2022-01-01", "base": "USD", "rates": {"EUR": "0.85"}},
            {"date": "2022-01-02", "base": "GBP", "rates": {"EUR": "1.15"}},
        ]
        result = self.adapter.get_historical_rates(
            "JPY", "EUR", datetime(2022, 1, 2)
        )
        self.assertIsNone(result)


class TestHttpJsonAdapter(unittest.TestCase):
    def setUp(self):
        self.provider_config = {
            "auth": {"access_key": "access_key"},
            "endpoints": {
                "latest": {
                    "request": {
                        "path": "/latest",
                        "args": {
                            "source_currency_code": "source",
                            "exchanged_currency_code": "exchanged",
                        },
                    },
                    "response": {"path": "rates"},
                },
                "historical": {
                    "request": {
                        "path": "/historical/$date",
                        "args": {
                            "source_currency_code": "source",
                            "exchanged_currency_code": "exchanged",
                        },
                    },
                    "response": {"path": "rates"},
                },
            },
        }
        self.adapter = HttpJsonAdapter("http://test.com", self.provider_config)

    @patch("requests.get")
    def test_get_latest_rate(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"USD": "1.23"}}
        mock_get.return_value = mock_response

        rate = self.adapter.get_latest_rate("EUR", "USD")

        self.assertEqual(rate, Decimal("1.23"))
        mock_get.assert_called_with(
            "http://test.com/latest",
            params={
                "access_key": "access_key",
                "source": "EUR",
                "exchanged": "USD",
            },
        )

    @patch("requests.get")
    def test_get_latest_rate_no_rate(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {}}
        mock_get.return_value = mock_response

        with self.assertRaises(ProviderError):
            self.adapter.get_latest_rate("EUR", "USD")

    @patch("requests.get")
    def test_get_historical_rates(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"2019-01-01": "1.23"}}
        mock_get.return_value = mock_response

        rates = self.adapter.get_historical_rates(
            "EUR", "USD", datetime(2019, 1, 1)
        )

        self.assertEqual(rates, {"2019-01-01": "1.23"})
        mock_get.assert_called_with(
            "http://test.com/historical/2019-01-01",
            params={
                "access_key": "access_key",
                "source": "EUR",
                "exchanged": "USD",
            },
        )

    @patch("requests.get")
    def test_get_historical_rates_no_rate(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {}}
        mock_get.return_value = mock_response

        with self.assertRaises(ProviderError):
            self.adapter.get_historical_rates(
                "EUR", "USD", datetime(2019, 1, 1)
            )
