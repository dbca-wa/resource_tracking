from django.conf.urls import url
from tracking.views import index, device, device_csv, get_vehicles, export_stop_start_points


urlpatterns = [
    url(r'^$', index, name='tracking_index'),
    url(r'^device/(?P<device_id>\d+)$', device, name='tracking_device'),
    url(r'^devices\.csv$', device_csv, name='tracking_device_csv'),
    url(r'^stop_start_points$', export_stop_start_points, name='stop_start_points_csv'),
    url(r'vehicle_data/', get_vehicles, name='get_fleet_vehicles'),
]
