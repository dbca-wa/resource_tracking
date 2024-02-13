from django.urls import path
from tracking import views


urlpatterns = [
    path("devices.csv", views.DevicesView.as_view(format="csv"), name="track_device_csv"),
    path("devices.geojson", views.DevicesView.as_view(), name="track_device_geojson"),
    path("loggedpoint/<int:device_id>.csv", views.DeviceHistoryView.as_view(format="csv"), name="device_history_view_csv"),
    path("loggedpoint/<int:device_id>.geojson", views.DeviceHistoryView.as_view(), name="device_history_view_geojson"),
    path("route/<int:device_id>.geojson", views.DeviceRouteView.as_view(), name="device_route_view_geojson"),
]
