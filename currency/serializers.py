from django.contrib.auth.models import Group, User
from rest_framework import serializers

from currency.models import CurrencyExchangeRate


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class CurrencyExchangeRateSerializer(
    serializers.HyperlinkedModelSerializer
):  # TODO: which subclass?
    class Meta:
        model = CurrencyExchangeRate
        fields = [
            "source_currency",
            "exchanged_currency",
            "valuation_date",
            "rate_value",
        ]


class CurrencyRateListSerializer(serializers.Serializer):
    source_currency = serializers.CharField(help_text="Source currency code")
    date_from = serializers.CharField(help_text="Start date YYYY-MM-DD")
    date_to = serializers.CharField(help_text="End date YYYY-MM-DD")


class CurrencyConverterSerializer(serializers.Serializer):
    source_currency = serializers.CharField(help_text="Source currency code")
    exchanged_currency = serializers.CharField(
        help_text="Exchanged currency code"
    )
    amount = serializers.CharField(help_text="Amount of source currency")


class TwrrSerializer(serializers.Serializer):
    source_currency = serializers.CharField(help_text="Source currency code")
    exchanged_currency = serializers.CharField(
        help_text="Exchanged currency code"
    )
    amount = serializers.CharField(help_text="Amount of source currency")
    start_date = serializers.CharField(help_text="Start date YYYY-MM-DD")
