from django.urls import path
from django.views.generic.base import RedirectView

from tracking import views

app_name = "tracking"
urlpatterns = [
    path("devices/", views.DeviceList.as_view(), name="device_list"),
    path("devices/download/", views.DeviceDownload.as_view(), name="device_download"),
    # FIXME: remove the view below after SSS is updated.
    path("devices/download/csv/", views.DeviceDownloadCsv.as_view(), name="device_download_csv"),
    path("devices/map/", views.DeviceMap.as_view(), name="device_map"),
    path("devices/<int:pk>/", views.DeviceDetail.as_view(), name="device_detail"),
    path("devices/<int:pk>/update/", views.DeviceUpdate.as_view(), name="device_update"),
    path("devices/<int:pk>/stream/", views.DeviceStream.as_view(), name="device_stream"),
    path("devices/<int:pk>/history/", views.DeviceHistoryDownload.as_view(), name="device_history"),
    path("devices/<int:pk>/route/", views.DeviceRouteDownload.as_view(), name="device_route"),
    # NOTE: the DeviceMetricsSource view is also registered under the /api path in order to allow basic auth.
    path("devices/metrics/<str:source_device_type>/", views.DeviceMetricsSource.as_view(), name="device_metrics_source"),
    # Older style route patterns, now redirected.
    path("map/", RedirectView.as_view(pattern_name="tracking:device_map", permanent=True)),
    path("devices.csv", RedirectView.as_view(pattern_name="tracking:device_download_csv", permanent=True, query_string=True)),
    path("devices.geojson", RedirectView.as_view(pattern_name="tracking:device_download", permanent=True, query_string=True)),
    path("loggedpoint/<int:pk>.csv", RedirectView.as_view(pattern_name="tracking:device_history", permanent=True, query_string=True)),
    path("loggedpoint/<int:pk>.geojson", RedirectView.as_view(pattern_name="tracking:device_history", permanent=True, query_string=True)),
    path("route/<int:pk>.geojson", RedirectView.as_view(pattern_name="tracking:device_route", permanent=True, query_string=True)),
    path("sss_admin/tracking/device/<int:pk>/change/", RedirectView.as_view(pattern_name="tracking:device_update", permanent=True)),
]
