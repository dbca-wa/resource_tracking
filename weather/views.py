from __future__ import absolute_import, unicode_literals
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render_to_response
from weather.models import WeatherStation, WeatherObservation
import pytz


def index(request):
    return render_to_response('weather/index.html', {
        'stations': WeatherStation.objects.filter(active=True)
    })


def weatherstation(request, station_id):
    return render_to_response('weather/station.html', {
        'station': WeatherStation.objects.get(pk=station_id)
    })


def observations_health(request):
    stations = []
    for i in WeatherStation.objects.filter(active=True):
        exp_obs = int(60 / i.connect_every)  # We expect this many observations/hour.
        s = {
            'name': i.name,
            'ip_address': i.ip_address,
            'port': i.port,
            'interval_minutes': i.connect_every,
            'last_reading': i.last_reading,
            'observations_expected_hr': exp_obs,
            'observations_actual_hr': 0,
            'observations_health': 'healthy'
        }

        # If the station has not met its expected number of observation for
        # the last hour, set observations_health to "warning".
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        diff = timedelta(seconds=(60 * 60) + 30)  # 1 h 30 s.
        obs = WeatherObservation.objects.filter(station=i, date__gte=now - diff).count()
        s['observations_actual_hr'] = obs
        if obs < exp_obs:
            s['observations_health'] = 'warning'

        # If the station has missed its last two observation intervals, set
        # observations_health to "error".
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        diff = timedelta(seconds=((60 * i.connect_every) * 2) + 10)  # Twice interval plus 10 s
        obs = WeatherObservation.objects.filter(station=i, date__gte=now - diff).count()
        if obs < 2:
            s['observations_health'] = 'error'

        stations.append(s)

    return JsonResponse({'objects': stations})
