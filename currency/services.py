import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import QuerySet

from currency.models import Currency, CurrencyExchangeRate, Provider
from currency.provider_interface import (
    FileJsonAdapter,
    HttpJsonAdapter,
    ProviderError,
)

logger = logging.getLogger("django")


def get_db_rates(
    source_currency_code: str,
    exchanged_currency_code: str,
    date_range: list[datetime],
) -> QuerySet:
    """
    Fetches the currency exchange rates from the database.

    Parameters:
    source_currency_code (str): The code of the source currency.
    date_range (list[datetime]): The date range for which to fetch the rates.

    Returns:
    QuerySet: The fetched currency exchange rates.
    """
    if source_currency_code == "EUR":
        return CurrencyExchangeRate.objects.select_related(
            "source_currency", "exchanged_currency"
        ).filter(
            source_currency__code=source_currency_code,
            exchanged_currency__code=exchanged_currency_code,
            valuation_date__range=date_range,
        )
    else:
        # TODO:
        # Fetch all rates and then reverse them based on EUR
        return CurrencyExchangeRate.objects.filter(
            valuation_date__range=date_range
        )


def process_db_rates(
    db_rates: QuerySet, source_currency_code: str, exchanged_currency_code: str
) -> list[dict]:
    """
    Processes the fetched currency exchange rates.

    Parameters:
    db_rates (QuerySet): The currency exchange rates fetched from the database.
    source_currency_code (str): The code of the source currency.

    Returns:
    list[dict]: The processed currency exchange rates.
    """
    result = list()
    rates_grouped_by_date = defaultdict(list)

    for row in db_rates.values(
        "valuation_date", "rate_value", "exchanged_currency__code"
    ):
        rates_grouped_by_date[row["valuation_date"]].append(row)

    for valuation_date, rates in rates_grouped_by_date.items():
        # TODO:
        if source_currency_code == "EUR":
            result.append(
                {
                    "date": valuation_date.strftime("%Y-%m-%d"),
                    "rates": {
                        r["exchanged_currency__code"]: r["rate_value"]
                        for r in rates
                    },
                }
            )
        else:
            try:
                base_rate = next(
                    item
                    for item in rates
                    if item["exchanged_currency__code"] == source_currency_code
                )
            except StopIteration:
                raise ValueError(
                    "No base rate found for currency code {}".format(
                        source_currency_code
                    )
                )

            processed_rates = {
                r["exchanged_currency__code"]: round(
                    r["rate_value"] / base_rate["rate_value"], 6
                )
                for r in rates
                if r["exchanged_currency__code"]
                != base_rate["exchanged_currency__code"]
            }
            result.append(
                {
                    "date": valuation_date,
                    "rates": processed_rates
                    | {"EUR": round(1 / base_rate["rate_value"], 6)},
                }
            )

    return result


def get_currency_rates_for_period(
    source_currency_code: str,
    exchanged_currency_code: str,
    date_from: datetime,
    date_to: datetime,
) -> list[dict]:
    """
    Fetches and processes the currency exchange rates for a specific period.

    Parameters:
    source_currency_code (str): The code of the source currency.
    exchanged_currency_code (str): The code of the exchanged currency.
    date_from (datetime): The start date of the period.
    date_to (datetime): The end date of the period.

    Returns:
    list[dict]: The processed currency exchange rates for the period.
    """
    date_range = [date_from, date_to]
    db_rates = get_db_rates(
        source_currency_code, exchanged_currency_code, date_range
    )
    return (
        process_db_rates(
            db_rates, source_currency_code, exchanged_currency_code
        )
        if db_rates
        else []
    )


def get_latest_from_provider(
    provider: Provider, source_currency_code: str, exchanged_currency_code: str
) -> dict:
    """This function retrieves the latest exchange rate from a given provider.

    Args:
        provider (Provider): The provider object which contains
            the resource type, address, config and base currency details.
        source_currency_code (str): The source currency code.
        exchanged_currency_code (str): The target currency code.

    Raises: ValueError: If the provider's resource type is unknown.

    Returns:
        dict: If the provider's base currency is not forced or
            matches the source currency code, it returns a dictionary
            with the latest exchange rate.
        Decimal: If the provider's base currency is forced and does not match
            the source currency code, it returns a Decimal representing
            the calculated exchange rate.
    """
    if provider.resource_type == "http":
        adapter = HttpJsonAdapter(provider.address, provider.config)
    elif provider.resource_type == "json":
        adapter = FileJsonAdapter(provider.address, provider.config)
    else:
        raise ValueError(
            "Unknown provider resource type: {}".format(provider.resource_type)
        )
    if (
        provider.force_base_currency
        and provider.force_base_currency != source_currency_code
    ):
        raw_data = adapter.get_latest_rate(
            source_currency_code=provider.force_base_currency,
            exchanged_currency_code=",".join(
                [exchanged_currency_code, source_currency_code]
            ),
        )
        return Decimal(
            raw_data[source_currency_code] / raw_data[exchanged_currency_code]
        )
    return adapter.get_latest_rate(
        source_currency_code=source_currency_code,
        exchanged_currency_code=exchanged_currency_code,
    )


def fetch_latest_rates_from_provider(
    source_currency_code: str, exchanged_currency_code: str
) -> Decimal:
    """
    Fetches the latest exchange rates from the provider
    with the highest priority.

    This function attempts to fetch the latest exchange rates
    from each provider in order of their priority.
    If a provider fails to provide the data, the function logs the error
    and proceeds to the next provider.

    Args:
        source_currency_code (str): The source currency code.
        exchanged_currency_code (str): The target currency code.

    Returns:
        Decimal: The latest exchange rate from the provider
            with the highest priority.

    """
    providers = Provider.objects.order_by("priority")
    data = None
    for provider in providers:
        try:
            data = get_latest_from_provider(
                provider, source_currency_code, exchanged_currency_code
            )
            if data:
                break
        except ProviderError:
            logger.error("Provider {} failed".format(provider.name))
            continue
    return data


def reverse_rates(source_currency_code: str, data: dict) -> dict:
    """
    Converts the rates in the input data dictionary from the base currency
    to the source currency.

    Args:
        source_currency_code (str): The source currency code.
        data (dict): A dictionary of currency codes and their corresponding
            rates against the base currency.

    Returns:
        dict: A dictionary of currency codes and their corresponding rates
            against the source currency.
            The rates are rounded to six decimal places.
    """
    try:
        base_rate = data[source_currency_code]
    except KeyError:
        return dict()
    reversed_data = {
        c: round(r / base_rate, 6)
        for c, r in data.items()
        if c != source_currency_code
    }
    return reversed_data


def get_hist_from_provider(
    provider: Provider,
    source_currency_code: str,
    exchanged_currency_code: str,
    valuation_date: datetime,
) -> dict:
    """
    This function retrieves historical exchange rates
    from a given exchange rates provider.

    Arguments:
        provider (Provider): The provider to retrieve data from.
            This provider must have a resource_type attribute
            that is either "http" or "json", and a force_base_currency
            attribute that is either None or a string
            representing a currency code.
        source_currency_code (str): The source currency code.
        exchanged_currency_code (str): The target currency code.
        valuation_date (datetime): The date of the exchange rate.

    Returns: dict: A dictionary containing the historical exchange rates.

    Raises: ValueError: If the provider's resource_type is not
        "http" or "json".
    """
    if provider.resource_type == "http":
        adapter = HttpJsonAdapter(provider.address, provider.config)
    elif provider.resource_type == "json":
        adapter = FileJsonAdapter(provider.address, provider.config)
    else:
        raise ValueError(
            "Unknown provider resource type: {}".format(provider.resource_type)
        )

    if (
        provider.force_base_currency
        and provider.force_base_currency != source_currency_code
    ):
        raw_data = adapter.get_historical_rates(
            source_currency_code=provider.force_base_currency,
            exchanged_currency_code=",".join(
                [exchanged_currency_code, source_currency_code]
            ),
            valuation_date=valuation_date,
        )
        return reverse_rates(source_currency_code, raw_data)
    return adapter.get_historical_rates(
        source_currency_code=source_currency_code,
        exchanged_currency_code=exchanged_currency_code,
        valuation_date=valuation_date,
    )


def fetch_historical_rates_from_provider(
    source_currency_code: str,
    exchanged_currency_code: str,
    valuation_date: datetime,
) -> dict:
    """
    Fetches historical exchange rates from a currency data provider.

    This function iterates over all providers sorted by their priority.
    It attempts to fetch the data from each provider
    until it finds a provider that can provide the data.

    After fetching the data, it creates CurrencyExchangeRate objects
    for each exchange rate and saves them to the database.

    Args:
        source_currency_code (str): The code of the source currency.
        exchanged_currency_code (str): The code of the exchanged currency.
        valuation_date (datetime): The date for which the rates are requested.

    Returns:
        dict: A dictionary containing the exchange rates.

    Raises:
        ValueError: If no data could be fetched from any provider.
    """
    providers = Provider.objects.order_by("priority")
    data = None
    for provider in providers:
        try:
            data = get_hist_from_provider(
                provider,
                source_currency_code,
                exchanged_currency_code,
                valuation_date,
            )
            if data:
                break
        except ProviderError:
            logger.error("Provider {} failed".format(provider.name))
            continue

    if data is not None:
        currencies = {
            c["code"]: c["id"]
            for c in Currency.objects.all().values("code", "id")
        }
        if "rates" in data:
            creates = [
                CurrencyExchangeRate(
                    source_currency_id=currencies[source_currency_code],
                    exchanged_currency_id=currencies[symbol],
                    rate_value=rate,
                    valuation_date=valuation_date,
                )
                for symbol, rate in data["rates"].items()
            ]
            CurrencyExchangeRate.objects.bulk_create(creates)
        else:
            CurrencyExchangeRate.objects.create(
                source_currency_id=currencies[source_currency_code],
                exchanged_currency_id=currencies[exchanged_currency_code],
                rate_value=data[exchanged_currency_code],
                valuation_date=valuation_date,
            )

    return data


def get_weighted_ror(
    source_currency_code: str,
    exchanged_currency_code: str,
    amount: Decimal,
    start_date: datetime,
) -> dict:
    """
    This function calculates the Time Weighted Rate of Return (TWRR)
    for a given amount of a source currency when exchanged to a target currency
    from a specified start date to the present day.

    Args:
        source_currency_code (str): The source currency code.
        exchanged_currency_code (str): The target currency code.
        amount (Decimal): The amount of source currency to be exchanged.
        start_date (datetime): The start date from which to calculate the TWRR.

    Returns:
        dict: The list of daily TWRR for the given amount of the source
            currency when exchanged to the target currency from the start date
            to the present day.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    historical_rates = get_currency_rates_for_period(
        source_currency_code=source_currency_code,
        exchanged_currency_code=exchanged_currency_code,
        date_from=start_date,
        date_to=today,
    )
    if not historical_rates:
        dt = start_date
        while dt <= today:
            rates = fetch_historical_rates_from_provider(
                source_currency_code=source_currency_code,
                exchanged_currency_code=exchanged_currency_code,
                valuation_date=dt,
            )
            historical_rates.append(rates)
            dt = dt + timedelta(days=1)
    twrrs = calculate_twrr(historical_rates, amount)
    result = {
        "base": source_currency_code,
        "exchanged": exchanged_currency_code,
        "amount": amount,
        "start_date": start_date,
        "twrr": twrrs,
    }
    return result


def calculate_twrr(historical_rates: list, amount: Decimal) -> list[dict]:
    """
    This function calculates the Time-Weighted Rate of Return (TWRR)
    for a given amount and a list of historical rates.

    Args:
        historical_rates (list): A list of dictionaries containing
            the historical rates. Each dictionary should have
            keys 'valuation_date' and 'rate_value'.
        amount (Decimal): The initial investment amount.

    Returns:
        list: A list of dictionaries containing the valuation date, rate value
        and the TWRR for each day.
    """
    twrr_values = list()
    total_return = Decimal(1)

    for i in range(1, len(historical_rates)):
        previous_rate = historical_rates[i - 1]["rate_value"]
        current_rate = historical_rates[i]["rate_value"]

        daily_return = current_rate / previous_rate
        total_return *= daily_return
        current_value = round(total_return * amount, 6)
        twrr_values.append(
            {
                "date": historical_rates[i]["valuation_date"],
                "rate_value": historical_rates[i]["rate_value"],
                "twrr": current_value,
            }
        )

    return twrr_values
