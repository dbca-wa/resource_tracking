from django.conf.urls import url
from tracking.views import index, device, print_map


urlpatterns = [
    url(r'^$', index, name='tracking_index'),
    url(r'^print$', print_map, name='tracking_print_map'),
    url(r'^device/(?P<device_id>\d+)$', device, name='tracking_device'),
]
