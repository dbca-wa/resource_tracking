from datetime import timedelta
from django.conf import settings
from django.core.exceptions import FieldError
from django.urls import path
from django.utils import timezone
from io import BytesIO
from tastypie import fields
from tastypie.cache import NoCache
from tastypie.http import HttpBadRequest
from tastypie.resources import ModelResource, ALL_WITH_RELATIONS
from tastypie.serializers import Serializer
import unicodecsv as csv

from tracking.models import Device, LoggedPoint


class CSVSerializer(Serializer):
    formats = settings.TASTYPIE_DEFAULT_FORMATS + ['csv']

    content_types = dict(
        Serializer.content_types.items() |
        [('csv', 'text/csv')])

    def to_csv(self, data, options=None):
        options = options or {}
        data = self.to_simple(data, options)
        raw_data = BytesIO()
        if 'objects' in data and data['objects']:
            fields = data['objects'][0].keys()
            writer = csv.DictWriter(raw_data, fields, dialect='excel', extrasaction='ignore')
            header = dict(zip(fields, fields))
            writer.writerow(header)
            for item in data['objects']:
                writer.writerow(item)

        return raw_data.getvalue()

    def from_csv(self, content):
        raw_data = BytesIO(content)
        data = []
        for item in csv.DictReader(raw_data):
            data.append(item)
        return data


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

    def prepend_urls(self):
        return [
            path(
                "<resource_name>/fields/<field_name>/".format(self._meta.resource_name),
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

    def build_filters(self, filters=None):
        """Override build_filters to allow filtering by seen_age__lte=<minutes>
        """
        if filters is None:
            filters = {}
        orm_filters = super(DeviceResource, self).build_filters(filters)

        if 'seen_age__lte' in filters:
            # Convert seen_age__lte to a timedelta
            td = timedelta(minutes=int(filters['seen_age__lte']))
            orm_filters['seen__gte'] = timezone.now() - td

        return orm_filters

    Meta = generate_meta(Device, {
        'cache': HttpCache(settings.DEVICE_HTTP_CACHE_TIMEOUT),
        'serializer': CSVSerializer(),
    })
    age_minutes = fields.IntegerField(attribute='age_minutes', readonly=True, null=True)
    age_colour = fields.CharField(attribute='age_colour', readonly=True, null=True)
    age_text = fields.CharField(attribute='age_text', readonly=True, null=True)
    icon = fields.CharField(attribute='icon', readonly=True)


class LoggedPointResource(APIResource):
    device = fields.IntegerField(attribute='device_id', readonly=True)
    Meta = generate_meta(LoggedPoint, {
        'cache': HttpCache(settings.HISTORY_HTTP_CACHE_TIMEOUT)
    })
