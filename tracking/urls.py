from django.urls import path
from tracking.views import index, device, device_csv, get_vehicles, export_stop_start_points


urlpatterns = [
    path('', index, name='tracking_index'),
    path('device/<int:device_id>/', device, name='tracking_device'),
    path('devices.csv', device_csv, name='tracking_device_csv'),
    path('stop_start_points', export_stop_start_points, name='stop_start_points_csv'),
    path('vehicle_data/', get_vehicles, name='get_fleet_vehicles'),
]
