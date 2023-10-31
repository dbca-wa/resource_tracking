from django.urls import path
from tracking.views import DevicesView, DeviceHistoryView, DeviceRouteView


urlpatterns = [
    path("devices.csv", DevicesView.as_view(format="csv"), name="track_device_csv"),
    path("devices.geojson", DevicesView.as_view(), name="track_device_geojson"),
    path("loggedpoint/<int:device_id>.csv", DeviceHistoryView.as_view(format="csv"), name="device_history_view_csv"),
    path("loggedpoint/<int:device_id>.geojson", DeviceHistoryView.as_view(), name="device_history_view_geojson"),
    path("route/<int:device_id>.geojson", DeviceRouteView.as_view(), name="device_route_view_geojson"),
]
