from django.contrib.admin import ModelAdmin, register
from django.contrib.gis.admin import GeoModelAdmin
from weather.models import WeatherStation, Location


@register(Location)
class LocationAdmin(GeoModelAdmin):
    openlayers_url = '//static.dpaw.wa.gov.au/static/libs/openlayers/2.13.1/OpenLayers.js'


@register(WeatherStation)
class WeatherStationAdmin(ModelAdmin):
    list_display = (
        'name', 'abbreviation', 'ip_address', 'last_reading',
        'battery_voltage', 'connect_every', 'active')
