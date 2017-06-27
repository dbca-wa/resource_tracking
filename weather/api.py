from tastypie import fields

from tracking.api import APIResource, generate_meta
from weather.models import Location, WeatherStation, WeatherObservation


class LocationResource(APIResource):
    Meta = generate_meta(Location)


class WeatherStationResource(APIResource):
    Meta = generate_meta(WeatherStation)


class WeatherObservationResource(APIResource):
    date = fields.CharField(attribute='local_date', readonly=True)
    rainfall = fields.DecimalField(attribute='actual_rainfall', readonly=True)
    dew_point = fields.DecimalField(attribute='dew_point', readonly=True)
    station_id = fields.IntegerField(attribute='station_id', readonly=True)
    station_name = fields.CharField(attribute='station__name', readonly=True)
    station_bom_abbreviation = fields.CharField(attribute='station__bom_abbreviation', readonly=True)
    Meta = generate_meta(WeatherObservation)
