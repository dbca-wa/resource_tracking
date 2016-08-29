from django.conf.urls import include, url
from django.contrib import admin

from resource_tracking.harvest import cron
from resource_tracking.api import v1_api
from tracking import urls as tracking_urls
from tracking.geojsonviews import geojson_patterns
from weather import urls as weather_urls

from tracking.admin import tracking_admin_site

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^sss_admin/', include(tracking_admin_site.urls)),
    url(r'^api/', include(v1_api.urls)),
    url(r'^weather/', include(weather_urls)),
    url(r'^cron', cron),
    url(r'^', include(tracking_urls)),
    url(r'^', include(geojson_patterns, namespace='geojson')),
]
