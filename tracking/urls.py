from django.conf.urls import url
from tracking.views import index, print_map, device, device_csv


urlpatterns = [
    url(r'^$', index, name='tracking_index'),
    url(r'^print$', print_map, name='tracking_print_map'),
    url(r'^device/(?P<device_id>\d+)$', device, name='tracking_device'),
    url(r'^devices\.csv$', device_csv, name='tracking_device_csv'),
]
