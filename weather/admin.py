from django.contrib.admin import ModelAdmin, register
from django.contrib.gis.admin import GeoModelAdmin
from weather.models import WeatherStation, Location


@register(Location)
class LocationAdmin(GeoModelAdmin):
    pass


@register(WeatherStation)
class WeatherStationAdmin(ModelAdmin):
    list_display = (
        'name', 'abbreviation', 'ip_address', 'last_reading',
        'battery_voltage', 'connect_every', 'active')
