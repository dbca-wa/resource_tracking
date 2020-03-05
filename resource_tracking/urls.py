from django.urls import include, path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from resource_tracking.api import v1_api
from tracking import urls as tracking_urls
from tracking.admin import tracking_admin_site
from tracking.harvest import harvest_tracking_email
from tracking.geojsonviews import geojson_patterns
#from weather import urls as weather_urls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sss_admin/', tracking_admin_site.urls),
    path('api/', include(v1_api.urls)),
    #path('weather/', include(weather_urls)),
    path('harvest_tracking_email', harvest_tracking_email),
    path('', include(tracking_urls)),
    path('', include(geojson_patterns)),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
