from datetime import timedelta, datetime
from django.core.serializers import serialize
from django.http import HttpResponse
from django.views.generic import View
from django.urls import path
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.gis.geos import LineString

from tracking.models import Device, LoggedPoint
from tracking.basic_auth import logged_in_or_basicauth


class GeojsonView(View):
    """
    Base class for geojosn view
    """
    http_method_names = ['get']

    _srid = None

    def __init__(self):
        """
        load settings from djago.conf.settings
        """
        tmp = self.srid

    @method_decorator(logged_in_or_basicauth(realm="Resource Tracking"))
    def dispatch(self, *args, **kwargs):
        return super(GeojsonView, self).dispatch(*args, **kwargs)


class DevicesView(GeojsonView):
    """
    Process http request and return devices as geojson
    """

    @property
    def srid(self):
        if DevicesView._srid is None:
            d = Device.objects.filter(point__isnull=False).first()
            if d:
                DevicesView._srid = d.point.srid

        return DevicesView._srid

    def get(self, request):
        """
        generate geojson data
        """
        try:
            days = int(request.GET.get("days", default=14))
        except:
            days = 14

        q = Device.objects.all()
        if days:
            q = q.filter(seen__gte=timezone.now() - timedelta(days=days))

        geojson = serialize(
            'geojson',
            q,
            geometry_field='point',
            srid=self.srid or "4326",
            properties=(
                'id',
                'deviceid',
                'name',
                'callsign',
                'symbol',
                'rego',
                'make',
                'model',
                'category',
                'heading',
                'velocity',
                'altitude',
                'seen',
                'age_minutes',
                'age_colour',
                'age_text',
                'icon'))

        geojson_type = ('application/vnd.geo+json', None)
        response = HttpResponse(geojson, content_type=geojson_type)

        return response


class LoggedPointView(GeojsonView):
    """
    Process http request and return device's history as geojson
    """
    @property
    def srid(self):
        if LoggedPointView._srid is None:
            d = LoggedPoint.objects.filter(point__isnull=False).first()
            if d:
                LoggedPointView._srid = d.point.srid

        return LoggedPointView._srid

    def get(self, request, deviceid=None):
        """
        generate geojson data
        """
        geojson = "{}"
        try:
            deviceid = int(deviceid)
        except:
            deviceid = None
        if deviceid:
            start = request.GET.get("start", default=None)
            if start is None:
                # start is missing, use the default value: one day before
                start = timezone.now() - timedelta(days=1)
            else:
                try:
                    # parsing the start date with the date format: iso 8601
                    start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                except:
                    # Failed to parse the start date, use the default value:
                    # one day before
                    start = timezone.now() - timedelta(days=1)

            end = request.GET.get("end", default=None)
            if end is not None:
                try:
                    # parsing the end date with the date format: iso 8601
                    end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                except:
                    end = None

            # ignore the bbox
            q = LoggedPoint.objects.filter(device_id=deviceid)

            if start:
                q = q.filter(seen__gte=start)

            if end:
                q = q.filter(seen__lt=end)

            geojson = self.get_geojson(q)

        geojson_type = ('application/vnd.geo+json', None)
        response = HttpResponse(geojson, content_type=geojson_type)

        return response

    def get_geojson(q):
        return "{}"


class HistoryView(LoggedPointView):
    """
    Process http request and return device's history as geojson
    """

    def get_geojson(self, q):
        """
        generate geojson data
        """
        return serialize('geojson', q, geometry_field='point', srid=self.srid or "4326", properties=(
            'id', 'heading', 'velocity', 'altitude', 'seen', 'raw', 'device_id'))


class RouteView(LoggedPointView):
    """
    Process http request and return device's route as geojson
    """

    def get_geojson(self, q):
        """
        generate geojson data
        """

        # add linestring spatial data and label to convert point to line.
        start_point = None
        for p in q:
            if start_point is not None:
                setattr(
                    start_point, "route", LineString(
                        start_point.point, p.point))
                setattr(
                    start_point,
                    "label",
                    "{0} to {1}".format(
                        start_point.seen.strftime(
                            "%H:%M:%S") if start_point.seen else "",
                        p.seen.strftime("%H:%M:%S") if p.seen else ""))

            start_point = p

        # exclude the last point, because the last point is not a line string.
        q = q[:len(q) - 1]

        return serialize('geojson', q, geometry_field='route', srid=self.srid or "4326", properties=(
            'id', 'heading', 'velocity', 'altitude', 'seen', 'raw', 'device_id', 'label'))


geojson_patterns = [
    path('devices.geojson', DevicesView.as_view()),
    path('loggedpoint/<int:device_id>.geojson', HistoryView.as_view()),
    path('route/<int:device_id>.geojson', RouteView.as_view()),
]
