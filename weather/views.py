from __future__ import absolute_import, unicode_literals
from django.shortcuts import render_to_response
from weather.models import WeatherStation


def index(request):
    return render_to_response('weather/index.html', {
        'stations': WeatherStation.objects.all()
    })


def weatherstation(request, station_id):
    return render_to_response('weather/station.html', {
        'station': WeatherStation.objects.get(pk=station_id)
    })
