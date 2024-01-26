import json
import os
import random
from datetime import datetime, timedelta
from itertools import permutations
from time import time

from celery import shared_task
from celery.utils.log import get_task_logger

from currency.models import Currency, CurrencyExchangeRate, Provider
from currency.provider_interface import FileJsonAdapter
from currency.services import fetch_historical_rates_from_provider

logger = get_task_logger(__name__)


@shared_task
def fetch_exchange_rates():
    """
    This task that fetches exchange rates for all available currency
    pairs from the previous day and writes them to the database.

    Returns: None
    """
    currencies = {
        c["code"]: c["id"] for c in Currency.objects.all().values("id", "code")
    }
    yesterday = datetime.today() + timedelta(days=-1)
    for pair in permutations(currencies, 2):
        fetch_historical_rates_from_provider(
            source_currency_code=pair[0],
            exchanged_currency_code=pair[1],
            valuation_date=yesterday,
        )

    logger.info("Exchange rates updated")


# @shared_task
def mock_historical_data_task():
    """
    This function generates mock historical data for currency exchange
    rates and writes it to a file.

    Returns: None
    """
    mock_provider = Provider.objects.filter(resource_type="json").first()
    adapter = FileJsonAdapter(mock_provider.address, mock_provider.config)
    yesterday = datetime.today() + timedelta(days=-1)
    file_path = os.path.join(adapter.address, adapter.historical_endpoint_path)
    with open(file_path, "r") as f:
        try:
            previous_rates = json.load(f)
        except json.JSONDecodeError:
            previous_rates = None
    if not previous_rates:
        previous_rates = [
        {
            "base": "EUR",
            "date": "2024-01-25",
            "rates": {"USD": 1.082573, "CHF": 0.939527, "GBP": 0.852586},
        },
        {
            "base": "USD",
            "date": "2024-01-25",
            "rates": {"EUR": 0.9235, "CHF": 0.8678, "GBP": 0.7874},
        },
        {
            "base": "CHF",
            "date": "2024-01-25",
            "rates": {"USD": 1.1522, "EUR": 1.0641, "GBP": 0.9076},
        },
        {
            "base": "GBP",
            "date": "2024-01-25",
            "rates": {"USD": 1.2700, "CHF": 1.1020, "EUR": 1.1725},
        },
        ]

    mock_rates_to_create = list()
    for currency in previous_rates:
        mock_rates_to_create.append(
            {
                "base": currency["base"],
                "date": yesterday.strftime("%Y-%m-%d"),
                "rates": {
                    k: round(v * random.uniform(0.8, 1.2), 6)
                    for k, v in currency["rates"].items()
                },
            }
        )

    with open(file_path, "w") as f:
        to_write = mock_rates_to_create + previous_rates
        f.writelines(json.dumps(to_write))
    logger.info("Mock historical rates updated.")
    return


@shared_task
def mock_latest_rates_task():
    """
    This function generates mock latest data for currency exchange
    rates and writes it to a file.

    Returns: None
    """
    mock_provider = Provider.objects.filter(resource_type="json").first()
    adapter = FileJsonAdapter(mock_provider.address, mock_provider.config)
    today = datetime.today()
    file_path = os.path.join(adapter.address, adapter.latest_endpoint_path)
    with open(file_path, "r") as f:
        try:
            previous_rates = json.load(f)
        except json.JSONDecodeError:
            previous_rates = None
    if not previous_rates:
        previous_rates = [
            {
                "timestamp": 1706198703,
                "base": "EUR",
                "date": "2024-01-25",
                "rates": {"USD": 1.082573, "CHF": 0.939527, "GBP": 0.852586},
            },
            {
                "timestamp": 1706198703,
                "base": "USD",
                "date": "2024-01-25",
                "rates": {"EUR": 0.9235, "CHF": 0.8678, "GBP": 0.7874},
            },
            {
                "timestamp": 1706198703,
                "base": "CHF",
                "date": "2024-01-25",
                "rates": {"USD": 1.1522, "EUR": 1.0641, "GBP": 0.9076},
            },
            {
                "timestamp": 1706198703,
                "base": "GBP",
                "date": "2024-01-25",
                "rates": {"USD": 1.2700, "CHF": 1.1020, "EUR": 1.1725},
            },
        ]
    mock_rates_to_create = list()
    for currency in previous_rates:
        mock_rates_to_create.append(
            {
                "timestamp": int(time()),
                "base": currency["base"],
                "date": today.strftime("%Y-%m-%d"),
                "rates": {
                    k: round(v * random.uniform(0.8, 1.2), 6)
                    for k, v in currency["rates"].items()
                },
            }
        )

    with open(file_path, "w") as f:
        to_write = [
            {
                "date": today.strftime("%Y-%m-%d"),
                "base": "EUR",
                "rates": mock_rates_to_create,
            },
        ]
        f.writelines(json.dumps(to_write))
    logger.info("Mock latest rates updated.")
    return
