from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path

from currency.forms import CurrencyConverterForm, ExchangeRateComparisonForm
from currency.models import Currency, CurrencyExchangeRate, Provider
from currency.services import fetch_latest_rates_from_provider


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "symbol"]


class ProviderAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "priority",
        "address",
        "config",
        "resource_type",
    ]
    ordering = ["priority"]


def chart_view(request):
    chart_data = list()
    labels = list()
    if request.method == "POST":
        form = ExchangeRateComparisonForm(request.POST)
        if form.is_valid():
            currency = form.cleaned_data["currency"]
            today = datetime.today().date()
            currency_rates = (
                CurrencyExchangeRate.objects.select_related(
                    "exchanged_currency"
                )
                .filter(
                    source_currency__code="EUR",
                    valuation_date__gte=today + timedelta(days=-30),
                    exchanged_currency__in=currency,
                )
                .values(
                    "valuation_date", "rate_value", "exchanged_currency__code"
                )
            ).order_by("valuation_date")

            for row in currency_rates:
                chart_data.append(
                    {
                        "x": row["valuation_date"],
                        "y": row["rate_value"],
                    }
                )
                if row["valuation_date"] not in labels:
                    labels.append(row["valuation_date"])

            return JsonResponse(
                {
                    "label": currency[0].name,
                    "data": chart_data,
                    "date_labels": labels,
                }
            )
    else:
        form = ExchangeRateComparisonForm()
    return render(
        request,
        "admin/chart_admin.html",
        {
            "title": "Exchange rates comparison between currencies",
            "form": form,
            "chart_data": chart_data,
        },
    )


def converter_view(request):
    result = None
    if request.method == "POST":
        if "action" in request.POST and request.POST["action"] == "reset":
            form = CurrencyConverterForm()
        else:
            form = CurrencyConverterForm(request.POST)
        if form.is_valid():
            source_currency = form.cleaned_data["source_currency"]
            exchanged_currency = form.cleaned_data["exchanged_currency"]
            amount = form.cleaned_data["amount"]

            rate_value = fetch_latest_rates_from_provider(
                source_currency_code=source_currency.code,
                exchanged_currency_code=exchanged_currency.code,
            )

            converted_amount = amount * Decimal(rate_value)
            result = "{0:.2f}".format(converted_amount)

            return render(
                request,
                "admin/currency_converter.html",
                {
                    "title": "Currency converter",
                    "form": form,
                    "result": result,
                },
            )
    else:
        form = CurrencyConverterForm()

    return render(
        request,
        "admin/currency_converter.html",
        {"title": "Currency converter", "form": form, "result": result},
    )


class CustomAdminCurrencySite(admin.AdminSite):
    def get_app_list(self, request, _=None):
        app_list = super().get_app_list(request)
        app_list += [
            {
                "name": "Currency back office site",
                "app_label": "currency",
                "models": [
                    {
                        "name": "Currency exchange rates comparison chart",
                        "object_name": "chart_admin",
                        "admin_url": "/admin/chart_admin",
                        "view_only": False,
                    },
                    {
                        "name": "Currency converter",
                        "object_name": "converter_admin",
                        "admin_url": "/admin/converter_admin",
                        "view_only": False,
                    },
                ],
            }
        ]
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path("chart_admin/", chart_view, name="admin-chart"),
            path("converter_admin/", converter_view, name="admin-converter"),
        ]
        return urls


custom_admin_site = CustomAdminCurrencySite(name="admin")
custom_admin_site.register(Currency, CurrencyAdmin)
custom_admin_site.register(Provider, ProviderAdmin)
