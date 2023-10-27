from datetime import datetime, timedelta
from django.contrib.gis.geos import LineString
from django.core.serializers import serialize
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import View

from tracking.api import CSVSerializer
from tracking.basic_auth import logged_in_or_basicauth
from tracking.models import Device, LoggedPoint


class GeojsonView(View):
    http_method_names = ['get']
    srid = 4326
    format = "geojson"

    @method_decorator(logged_in_or_basicauth(realm="Resource Tracking"))
    def dispatch(self, *args, **kwargs):
        return super(GeojsonView, self).dispatch(*args, **kwargs)


class DevicesView(GeojsonView):

    def get(self, request, *args, **kwargs):

        if "days" in request.GET and request.GET["days"]:
            days = request.GET["days"]
        else:
            days = 14

        qs = Device.objects.filter(seen__gte=timezone.now() - timedelta(days=days))

        # CSV format download
        if self.format == "csv":
            data = {"objects": []}
            for device in qs:
                d = device.__dict__
                d.pop("_state", None)
                data["objects"].append(d)

            serializer = CSVSerializer()
            content = serializer.to_csv(data)
            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f'tracking_devices_{timestamp}.csv'
            response = HttpResponse(
                content,
                content_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'},
            )
        # GeoJSON format download
        else:
            geojson = serialize(
                'geojson',
                qs,
                geometry_field='point',
                srid=self.srid,
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
                    'icon',
                )
            )

            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f'tracking_devices_{timestamp}.geojson'
            response = HttpResponse(
                geojson,
                content_type='application/vnd.geo+json',
                headers={'Content-Disposition': f'attachment; filename={filename}'},
            )

        return response


class LoggedPointView(GeojsonView):
    """
    Process http request and return device's history as geojson
    """

    def dispatch(self, *args, **kwargs):
        if "device_id" not in self.kwargs:
            return HttpResponseBadRequest("Missing device_id")

        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        geojson = "{}"

        deviceid = kwargs["device_id"]
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

        response = HttpResponse(geojson, content_type='application/vnd.geo+json')

        return response

    def get_geojson(q):
        return "{}"


class HistoryView(LoggedPointView):

    def get_geojson(self, qs):

        return serialize(
            'geojson',
            qs,
            geometry_field='point',
            srid=self.srid,
            properties=(
                'id', 'heading', 'velocity', 'altitude', 'seen', 'raw', 'device_id',
            ),
        )


class RouteView(LoggedPointView):

    def get_geojson(self, q):

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

        return serialize(
            'geojson',
            q,
            geometry_field='route',
            srid=self.srid,
            properties=(
                'id', 'heading', 'velocity', 'altitude', 'seen', 'raw', 'device_id', 'label',
            ),
        )
