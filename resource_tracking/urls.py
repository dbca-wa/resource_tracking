from django.conf.urls import include, url

from .harvest import cron
from tracking.views import index, device, v1_api, print_map
from tracking.admin import site
from tracking.geojsonviews import geojson_patterns

urlpatterns = [
    url(r'^admin/', include(site.urls)),
    url(r'^api/', include(v1_api.urls)),
    url(r'^cron', cron),
    url(r'^$', index),
    url(r'^print$', print_map),
    url(r'^device/(?P<device>\d+)$', device),
    url(r'^', include(geojson_patterns, namespace='geojson')),
]
