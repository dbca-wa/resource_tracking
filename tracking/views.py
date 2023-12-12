from datetime import datetime, timedelta
from django.contrib.gis.geos import LineString
from django.core.serializers import serialize
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.generic import View

from tracking.api import CSVSerializer
from tracking.models import Device, LoggedPoint


class SpatialDataView(View):
    """Base view to return a queryset of spatial data as GeoJSON or CSV.
    """
    model = None
    http_method_names = ["get"]
    srid = 4326
    format = "geojson"
    geometry_field = None
    properties = ()
    filename_prefix = None

    def get_filename_prefix(self):
        if not self.filename_prefix:
            return self.model._meta.model_name

        return self.filename_prefix

    def get_queryset(self):
        return self.model.objects.all()

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        filename_prefix = self.get_filename_prefix()

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
            filename = f"{filename_prefix}_{timestamp}.csv"
            response = HttpResponse(
                content,
                content_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        # GeoJSON format download
        else:
            geojson = serialize(
                "geojson",
                qs,
                geometry_field=self.geometry_field,
                srid=self.srid,
                properties=self.properties,
            )

            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f"{filename_prefix}_{timestamp}.geojson"
            response = HttpResponse(
                geojson,
                content_type="application/vnd.geo+json",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        return response


class DevicesView(SpatialDataView):
    """Return structured data about tracking devices seen in the previous n days
    (14 by default).
    """
    model = Device
    geometry_field = "point"
    properties = (
        "id",
        "deviceid",
        "name",
        "callsign",
        "symbol",
        "rego",
        "make",
        "model",
        "category",
        "heading",
        "velocity",
        "altitude",
        "seen",
        "age_minutes",
        "age_colour",
        "age_text",
        "icon",
    )
    filename_prefix = "tracking_devices"

    def get_queryset(self):
        qs = super().get_queryset()

        if "days" in self.request.GET and self.request.GET["days"]:
            days = int(self.request.GET["days"])
        else:
            days = 14
        qs = qs.filter(seen__gte=timezone.now() - timedelta(days=days))

        return qs


class DeviceHistoryView(SpatialDataView):
    """Return structured data of the tracking points for a single device over the previous n days
    (14 by default).
    """
    model = LoggedPoint
    geometry_field = "point"
    properties = ("id", "heading", "velocity", "altitude", "seen", "raw", "device_id")

    def dispatch(self, *args, **kwargs):
        if "device_id" not in self.kwargs:
            return HttpResponseBadRequest("Missing device_id")
        return super().dispatch(*args, **kwargs)

    def get_filename_prefix(self):
        device_id = self.kwargs["device_id"]
        device = Device.objects.get(pk=device_id)
        return f"{device.deviceid}_loggedpoint"

    def get_queryset(self):
        qs = super().get_queryset()

        device_id = self.kwargs["device_id"]
        qs = qs.filter(device_id=device_id)

        start = self.request.GET.get("start", default=None)
        if start is None:
            # start is missing, use the default value: 14 days before
            start = timezone.now() - timedelta(days=14)
        else:
            try:
                # Parse the start date as ISO8601 date format
                start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
            except:
                return HttpResponseBadRequest("Bad start format, use ISO8601")
        qs = qs.filter(seen__gte=start)

        end = self.request.GET.get("end", default=None)
        if end is not None:
            try:
                # Parse the end date as ISO8601 date format
                end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
            except:
                return HttpResponseBadRequest("Bad end format, use ISO8601")

            qs = qs.filter(seen__lt=end)

        return qs


class DeviceRouteView(DeviceHistoryView):
    """Extend the DeviceHistoryView to return a device's route history as a LineString geometry.
    This view only returns GeoJSON, not CSV.
    """
    def get(self, request, *args, **kwargs):
        """Override this method to return a linestring dataset instead of points.
        """
        qs = self.get_queryset()
        device_id = self.kwargs["device_id"]
        device = Device.objects.get(pk=device_id)
        filename_prefix = f"{device.deviceid}_route"

        start_point = None

        # Modify the query of LoggedPoint objects in-place: set an attribute called `route` on
        # each point consisting of a LineString geometry having a start and end point.
        # Start point is the LoggedPoint, end point is the next instance.
        # Also add a `label` attribute that captures the timestamps of each.
        for loggedpoint in qs:
            if start_point is not None:
                setattr(start_point, "route", LineString(start_point.point, loggedpoint.point))
                start_label = start_point.seen.strftime("%H:%M:%S")
                end_label = loggedpoint.seen.strftime("%H:%M:%S")
                setattr(start_point, "label", f"{start_label} to {end_label}")
            start_point = loggedpoint

        # Exclude the last loggedpoint in the queryset because it won't have the `route` attribute.
        qs = qs[:len(qs) - 1]

        geojson = serialize(
            "geojson",
            qs,
            geometry_field="route",
            srid=self.srid,
            properties=(
                "id", "heading", "velocity", "altitude", "seen", "raw", "device_id", "label",
            ),
        )
        timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
        filename = f"{filename_prefix}_{timestamp}.geojson"
        response = HttpResponse(
            geojson,
            content_type="application/vnd.geo+json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

        return response
