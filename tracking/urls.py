from django.urls import path
from tracking import views


urlpatterns = [
    path("map/", views.ResourceMap.as_view(), name="resource_map"),
    path("devices.csv", views.DeviceView.as_view(format="csv"), name="device_csv"),
    path("devices.geojson", views.DeviceView.as_view(), name="device_geojson"),
    path("loggedpoint/<int:device_id>.csv", views.DeviceHistoryView.as_view(format="csv"), name="device_history_csv"),
    path("loggedpoint/<int:device_id>.geojson", views.DeviceHistoryView.as_view(), name="device_history_geojson"),
    path("route/<int:device_id>.geojson", views.DeviceRouteView.as_view(), name="device_route_geojson"),
]
