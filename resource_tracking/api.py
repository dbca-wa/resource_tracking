from django.conf.urls import url
from django.core.exceptions import FieldError

from tastypie.http import HttpBadRequest
from tastypie.resources import ModelResource, ALL_WITH_RELATIONS
from tastypie.authentication import BasicAuthentication
from tastypie.authorization import DjangoAuthorization

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
        #'authentication':  BasicAuthentication(realm="Resource Tracking"),
        #'authorization': DjangoAuthorization()
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


