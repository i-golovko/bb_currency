from django.db import models


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=25, db_index=True)
    symbol = models.CharField(max_length=10)

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"

    def __str__(self):
        return self.name


class CurrencyExchangeRate(models.Model):
    source_currency = models.ForeignKey(
        Currency, related_name="exchanges", on_delete=models.CASCADE
    )
    exchanged_currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    valuation_date = models.DateField(db_index=True)
    rate_value = models.DecimalField(
        db_index=True, decimal_places=6, max_digits=18
    )

    class Meta:
        verbose_name = "Currency Exchange Rate"
        verbose_name_plural = "Currency Exchange Rates"
        ordering = ["valuation_date"]


class Provider(models.Model):
    RESOURCE_TYPE_CHOICES = (
        ("http", "HTTP Resource"),
        ("json", "JSON File"),
        ("csv", "CSV File"),
    )
    name = models.CharField(max_length=25, unique=True)
    priority = models.IntegerField()
    address = models.CharField(max_length=250)
    config = models.JSONField()
    resource_type = models.CharField(
        max_length=100, choices=RESOURCE_TYPE_CHOICES
    )
    force_base_currency = models.CharField(max_length=3, null=True, blank=True)

    class Meta:
        verbose_name = "Provider"
        verbose_name_plural = "Providers"
        ordering = ["priority"]

    def __str__(self):
        return self.name
