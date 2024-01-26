from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CurrencyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "currency"


class CustomAdminConfig(AdminConfig):
    default_site = "currency.admin.CustomAdminCurrencySite"
