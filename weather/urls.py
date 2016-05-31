from django.conf.urls import url
from weather.views import index, weatherstation


urlpatterns = [
    url(r'^$', index, name='weather_index'),
    url(r'^station/(?P<station_id>\d+)$', weatherstation, name='weather_station')
]
