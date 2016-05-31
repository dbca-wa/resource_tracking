from tastypie import fields

from tracking.api import APIResource, generate_meta
from weather.models import Location, WeatherStation, WeatherObservation


class LocationResource(APIResource):
    Meta = generate_meta(Location)


class WeatherStationResource(APIResource):
    Meta = generate_meta(WeatherStation)


class WeatherObservationResource(APIResource):
    date = fields.CharField(attribute='local_date', readonly=True)
    # TODO: dew_point and rainfall should be calculated on save and served straight from db
    # rainfall = fields.DecimalField(attribute='get_rainfall', readonly=True)
    dew_point = fields.DecimalField(attribute='dew_point', readonly=True)
    station = fields.IntegerField(attribute='station_id', readonly=True)
    Meta = generate_meta(WeatherObservation)
