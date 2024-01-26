from django import forms
from django.forms import ModelChoiceField, ModelMultipleChoiceField
from django.forms.fields import DecimalField

from currency.models import Currency


class CurrencyConverterForm(forms.Form):
    source_currency = ModelChoiceField(
        queryset=Currency.objects.all(), to_field_name="code"
    )
    exchanged_currency = ModelChoiceField(
        queryset=Currency.objects.all(), to_field_name="code"
    )
    amount = DecimalField(max_digits=10, decimal_places=2)


class ExchangeRateComparisonForm(forms.Form):
    currency = ModelMultipleChoiceField(
        queryset=Currency.objects.all().exclude(code="EUR"),
        to_field_name="code",
    )
