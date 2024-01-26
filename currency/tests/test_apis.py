from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from currency.models import Provider


class CurrencyRateListTests(APITestCase):
    url = reverse("currency-rate-list")

    def setUp(self):
        Provider.objects.create(
            name="Test JSON Provider",
            priority=1,
            address="assets/",
            resource_type="json",
            config={
                "auth": {},
                "endpoints": {
                    "latest": {
                        "request": {
                            "path": "mock_latest.json",
                            "args": {
                                "source_currency_code": "base",
                                "exchanged_currency_code": "symbols",
                            },
                        },
                        "response": {"path": "rates"},
                    },
                    "historical": {
                        "request": {
                            "path": "mock_historical.json",
                            "args": {
                                "source_currency_code": "base",
                                "exchanged_currency_code": "symbols",
                            },
                        },
                        "response": {"path": "rates"},
                    },
                },
            },
        )

        Provider.objects.create(
            name="Test HTTP Provider",
            priority=1,
            address="http://data.fixer.io/api/",
            resource_type="http",
            config={
                "auth": {"type": "query_param", "access_key": ""},
                "domain": "http://data.fixer.io/api/",
                "endpoints": {
                    "latest": {
                        "request": {
                            "args": {
                                "access_key": "access_key",
                                "source_currency_code": "base",
                                "exchanged_currency_code": "symbols",
                            },
                            "path": "latest",
                        },
                        "response": {"path": "rates"},
                    },
                    "historical": {
                        "request": {
                            "args": {
                                "access_key": "access_key",
                                "source_currency_code": "base",
                                "exchanged_currency_code": "symbols",
                            },
                            "path": "$date",
                        },
                        "response": {"path": "rates"},
                    },
                },
            },
        )

    @patch("currency.views.get_currency_rates_for_period")
    def test_successful_response_from_db(self, mock_rates_from_db):
        mock_rates_from_db.return_value = [
            {
                "date": "2024-01-01",
                "rates": {
                    "USD": Decimal("1.103769"),
                    "GBP": Decimal("0.867209"),
                    "CHF": Decimal("0.929318"),
                },
            }
        ]
        response = self.client.get(
            self.url,
            {
                "source_currency": "EUR",
                "date_from": "2024-01-01",
                "date_to": "2024-01-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_rates_from_db.assert_called()

    @patch("currency.views.fetch_historical_rates_from_provider")
    def test_response_from_provider(self, mock_rates_from_provider):
        mock_rates_from_provider.return_value = {
            "date": "2022-01-01",
            "EUR": 0.879395,
            "GBP": 0.739017,
            "CHF": 0.911704,
        }

        response = self.client.get(
            self.url,
            {
                "source_currency": "EUR",
                "date_from": "2024-01-01",
                "date_to": "2024-01-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_rates_from_provider.assert_called()

    def test_currency_no_required_params(self):
        response = self.client.get(self.url, {"source_currency": "MUR"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_data_response(self):
        response = self.client.get(
            self.url,
            {
                "source_currency": "",
                "date_from": "2021-01-01",
                "date_to": "2021-01-31",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_response_no_data(self):
        response = self.client.get(
            self.url,
            {
                "source_currency": "MUR",
                "date_from": "2021-01-01",
                "date_to": "2021-01-31",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    # @patch("currency.views.HttpJsonAdapter")  # Mock the adapters
    # @patch("currency.views.FileJsonAdapter")
    # def test_different_provider_types(
    #     self, mock_file_adapter, mock_http_adapter
    # ):
    #     self.client.get(
    #         self.url,
    #         {
    #             "source_currency": "EUR",
    #             "date_from": "2021-01-01",
    #             "date_to": "2021-01-31",
    #         },
    #     )

    #     mock_file_adapter.assert_called()
    #     mock_http_adapter.assert_not_called()


class CurrencyConverterTests(APITestCase):
    url = reverse("currency-converter")

    @patch("currency.views.fetch_latest_rates_from_provider")
    def test_successful_conversion(self, mock_fetch_latest_data):
        mock_fetch_latest_data.return_value = Decimal(1.2)
        amount = 100

        response = self.client.get(
            self.url,
            {
                "source_currency": "USD",
                "exchanged_currency": "EUR",
                "amount": amount,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            mock_fetch_latest_data.return_value * Decimal(amount),
        )

    def test_converter_no_required_params(self):
        response = self.client.get(
            self.url,
            {
                "source_currency": "",
                "exchanged_currency": "EUR",
                "amount": 100,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TWRRViewTests(APITestCase):
    url = reverse("twrr")

    @patch("currency.views.get_weighted_ror")
    def test_successful_twrr_calculation(self, mock_get_weighted_ror):
        # Mock the TWRR calculation function
        mock_data = [
            {
                "date": "2024-01-24",
                "base": "EUR",
                "rates": {
                    "EUR": 0.900611,
                    "USD": 1.075402,
                    "GBP": 0.89816,
                    "CHF": 0.847297,
                },
            },
            {
                "date": "2024-01-23",
                "rates": {
                    "EUR": 1.0,
                    "USD": 1.084776,
                    "GBP": 0.855128,
                    "CHF": 0.944454,
                },
            },
        ]
        mock_get_weighted_ror.return_value = mock_data

        response = self.client.get(
            self.url,
            {
                "source_currency": "USD",
                "exchanged_currency": "EUR",
                "amount": "100",
                "start_date": "2024-01-23",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_data)

    def test_invalid_data_response(self):
        response = self.client.get(
            self.url,
            {
                "source_currency": "",
                "exchanged_currency": "EUR",
                "amount": "100",
                "start_date": "2021-01-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
