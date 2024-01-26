from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import routers

from currency import views
from currency.admin import chart_view, converter_view, custom_admin_site

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            template_name="swagger-ui.html", url_name="schema"
        ),
        name="swagger-ui",
    ),
    path(
        "admin/chart_admin/",
        admin.site.admin_view(chart_view),
        name="chart-admin",
    ),
    path(
        "admin/converter_admin/",
        admin.site.admin_view(converter_view),
        name="converter-admin",
    ),
    # path("admin/", admin.site.urls),
    path("admin/", custom_admin_site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path(
        "rates/",
        views.CurrencyRateListView.as_view(),
        name="currency-rate-list",
    ),
    path(
        "convert/",
        views.CurrencyConverterView.as_view(),
        name="currency-converter",
    ),
    path("twrr/", views.TWRRView.as_view(), name="twrr"),
]
