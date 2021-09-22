from django.urls import include, path
from django.contrib import admin
from django.conf import settings
from django.views.generic.base import RedirectView

from resource_tracking.api import v1_api
from tracking import urls as tracking_urls
from tracking.admin import tracking_admin_site
from tracking.geojsonviews import geojson_patterns


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sss_admin/', tracking_admin_site.urls),
    path('api/', include(v1_api.urls)),
    path('', include(tracking_urls)),
    path('', include(geojson_patterns)),
    path(
        'favicon.ico',
        RedirectView.as_view(url='{}favicon.ico'.format(settings.STATIC_URL)),
        name='favicon'
    ),
]
