from tastypie.api import Api
from tracking.api import DeviceResource


v1_api = Api(api_name="v1")
v1_api.register(DeviceResource())
