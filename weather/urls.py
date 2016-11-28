from django.conf.urls import url
from weather.views import index, weatherstation, observations_health


urlpatterns = [
    url(r'^$', index, name='weather_index'),
    url(r'^observations-health/$', observations_health, name='observations_health'),
    url(r'^station/(?P<station_id>\d+)$', weatherstation, name='weather_station')
]
