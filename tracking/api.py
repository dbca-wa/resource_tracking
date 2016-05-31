from datetime import timedelta
from django.conf import settings
from django.conf.urls import url
from django.core.exceptions import FieldError
from django.utils import timezone
from tastypie import fields
from tastypie.cache import NoCache
from tastypie.http import HttpBadRequest
from tastypie.resources import ModelResource, ALL_WITH_RELATIONS

from tracking.models import Device, LoggedPoint


def generate_filtering(mdl):
    """Utility function to add all model fields to filtering whitelist.
    See: http://django-tastypie.readthedocs.org/en/latest/resources.html#basic-filtering
    """
    filtering = {}
    for field in mdl._meta.fields:
        filtering.update({field.name: ALL_WITH_RELATIONS})
    return filtering


def generate_meta(klass, overrides={}):
    metaitems = {
        'queryset': klass.objects.all(),
        'resource_name': klass._meta.model_name,
        'filtering': generate_filtering(klass),
    }
    metaitems.update(overrides)
    return type('Meta', (object,), metaitems)


class APIResource(ModelResource):
    class Meta:
        pass

    def prepend_urls(self):
        return [
            url(
                r"^(?P<resource_name>{})/fields/(?P<field_name>[\w\d_.-]+)/$".format(self._meta.resource_name),
                self.wrap_view('field_values'), name="api_field_values"),
        ]

    def field_values(self, request, **kwargs):
        # Get a list of unique values for the field passed in kwargs.
        try:
            qs = self._meta.queryset.values_list(kwargs['field_name'], flat=True).distinct()
        except FieldError as e:
            return self.create_response(request, data={'error': str(e)}, response_class=HttpBadRequest)
        # Prepare return the HttpResponse.
        return self.create_response(request, data=list(qs))


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
        "cache": HttpCache(settings.DEVICE_HTTP_CACHE_TIMEOUT)
    })


class LoggedPointResource(APIResource):
    device = fields.IntegerField(attribute='device_id', readonly=True)
    Meta = generate_meta(LoggedPoint, {
        "cache": HttpCache(settings.HISTORY_HTTP_CACHE_TIMEOUT)
    })
