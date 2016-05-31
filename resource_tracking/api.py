from tastypie.api import Api
from tracking.api import DeviceResource, LoggedPointResource
from weather.api import LocationResource, WeatherStationResource, WeatherObservationResource


v1_api = Api(api_name='v1')
v1_api.register(DeviceResource())
v1_api.register(LoggedPointResource())
v1_api.register(LocationResource())
v1_api.register(WeatherStationResource())
v1_api.register(WeatherObservationResource())
