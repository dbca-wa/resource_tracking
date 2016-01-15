from __future__ import absolute_import, unicode_literals
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render_to_response
from django.conf import settings
from tastypie import fields
from tastypie.api import Api
from tastypie.cache import NoCache

from resource_tracking.api import APIResource, generate_meta
from .models import Device, LoggedPoint


def index(request):
    return render_to_response("index.html", {
        "settings": settings,
        "user": request.user
    })

def print_map(request):
    return render_to_response("print.html", {
        "settings": settings
    })

def device(request, device):
    return render_to_response("device.html", {
        "device": Device.objects.get(id=device)
    })

class HttpCache(NoCache):
    """
    Just set the cache control header to implement web cache
    """

    def __init__(self, timeout=0, public=None,
                 private=None, *args, **kwargs):
        """
        Optionally accepts a ``timeout`` in seconds for the resource's cache.
        Defaults to ``0`` seconds.
        """
        super(NoCache, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.public = public
        self.private = private

    def cache_control(self):
        control = {
            'max_age': self.timeout,
            's_maxage': self.timeout,
        }

        if self.public is not None:
            control["public"] = self.public

        if self.private is not None:
            control["private"] = self.private

        return control

class DeviceResource(APIResource):
    age_minutes = fields.IntegerField(attribute='age_minutes', readonly=True)
    age_colour = fields.CharField(attribute='age_colour', readonly=True)
    age_text = fields.CharField(attribute='age_text', readonly=True)
    icon = fields.CharField(attribute='icon', readonly=True)
    Meta = generate_meta(Device, {
        "queryset": Device.objects.filter(seen__gte=timezone.now() - timedelta(days=14)),
        "cache":HttpCache(settings.DEVICE_HTTP_CACHE_TIMEOUT)
    })


class LoggedPointResource(APIResource):
    device = fields.IntegerField(attribute='device_id', readonly=True)
    Meta = generate_meta(LoggedPoint,{
        "cache":HttpCache(settings.HISTORY_HTTP_CACHE_TIMEOUT)
    })

v1_api = Api(api_name='v1')
v1_api.register(DeviceResource())
v1_api.register(LoggedPointResource())
