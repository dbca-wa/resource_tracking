from django.urls import path
from django.views.generic.base import RedirectView

from tracking import views

urlpatterns = [
    path("devices/", views.DeviceList.as_view(), name="device_list"),
    path("devices/download/", views.DeviceListDownload.as_view(), name="device_download"),
    path("devices/map/", views.DeviceMap.as_view(), name="device_map"),
    path("devices/<int:pk>/", views.DeviceDetail.as_view(), name="device_detail"),
    path("devices/<int:pk>/stream/", views.DeviceStream.as_view(), name="device_stream"),
    path("devices/<int:pk>/history/", views.DeviceHistoryDownload.as_view(), name="device_history"),
    path("devices/<int:pk>/route/", views.DeviceRouteDownload.as_view(), name="device_route"),
    path(
        "devices/metrics/<str:source_device_type>/",
        views.DeviceMetricsSource.as_view(),
        name="device_metrics_source",
    ),
    # Older style route patterns, now redirected.
    path("map/", RedirectView.as_view(pattern_name="device_map", permanent=True)),
    path("devices.csv", RedirectView.as_view(pattern_name="device_download", permanent=True)),
    path("devices.geojson", RedirectView.as_view(pattern_name="device_download", permanent=True)),
    path("loggedpoint/<int:pk>.csv", RedirectView.as_view(pattern_name="device_history", permanent=True)),
    path("loggedpoint/<int:pk>.geojson", RedirectView.as_view(pattern_name="device_history", permanent=True)),
    path("route/<int:pk>.geojson", RedirectView.as_view(pattern_name="device_route", permanent=True)),
]
