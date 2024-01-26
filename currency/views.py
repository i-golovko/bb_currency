from datetime import timedelta
from decimal import Decimal

from dateutil.parser import parse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from currency.models import Currency
from currency.serializers import (
    CurrencyConverterSerializer,
    CurrencyRateListSerializer,
    TwrrSerializer,
)
from currency.services import (
    fetch_historical_rates_from_provider,
    fetch_latest_rates_from_provider,
    get_currency_rates_for_period,
    get_weighted_ror,
)


class CurrencyRateListView(APIView):
    """
    List of exchanged rates of source currency for each available currency
    for a given period

    Args:
        source currency code, start date, end date

    Returns:
        list of rate values
    """

    permission_classes = [AllowAny]

    @extend_schema(parameters=[CurrencyRateListSerializer])
    def get(self, request, *args, **kwargs):
        serializer = CurrencyRateListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        source_currency = params.get("source_currency")
        date_from = parse(params.get("date_from"))
        date_to = parse(params.get("date_to"))

        other_currencies = ",".join(
            Currency.objects.all()
            .exclude(code=source_currency)
            .values_list("code", flat=True)
        )

        period_rates = get_currency_rates_for_period(
            source_currency_code=source_currency.upper(),
            exchanged_currency_code=other_currencies,
            date_from=date_from,
            date_to=date_to,
        )
        if not period_rates:
            period_rates = list()
            dt = date_from
            while dt <= date_to:
                rates = fetch_historical_rates_from_provider(
                    source_currency_code=source_currency.upper(),
                    exchanged_currency_code=other_currencies,
                    valuation_date=dt,
                )
                if rates:
                    period_rates.append(rates)
                dt = dt + timedelta(days=1)

        return Response(period_rates)


class CurrencyConverterView(APIView):
    """
    Converts given amount of source currency into exchanged currency
    based on latest exchanged rate

    Args:
        source currency code,
        exchanged currency code,
        amount of source currency

    Returns:
        amount of converted currency
    """

    permission_classes = [AllowAny]

    @extend_schema(parameters=[CurrencyConverterSerializer])
    def get(self, request, *args, **kwargs):
        serializer = CurrencyConverterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        source_currency_code = params.get("source_currency")
        amount = Decimal(params.get("amount"))
        exchanged_currency_code = params.get("exchanged_currency")

        rate = fetch_latest_rates_from_provider(
            source_currency_code=source_currency_code,
            exchanged_currency_code=exchanged_currency_code,
        )
        if not rate:
            return Response(
                "Failed to fetch latest rates",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        res = amount * rate
        return Response(res)


class TWRRView(APIView):
    """
    Time-weighted rates of return for any given amount invested
    from source currency into exchanged one from start date until today

    Args:
        source currency code,
        exchanged currency code,
        amount or source currency,
        start date

    Returns:
        list of daily weighted rate of returns for the period
    """

    permission_classes = [AllowAny]

    @extend_schema(parameters=[TwrrSerializer])
    def get(self, request, *args, **kwargs):
        serializer = TwrrSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        source_currency = params.get("source_currency")
        amount = params.get("amount")
        exchanged_currency = params.get("exchanged_currency")
        start_date = parse(params.get("start_date"))

        data = get_weighted_ror(
            source_currency_code=source_currency.upper(),
            exchanged_currency_code=exchanged_currency.upper(),
            amount=Decimal(amount),
            start_date=start_date,
        )
        return Response(data)
