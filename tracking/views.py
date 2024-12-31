import asyncio
from datetime import datetime, timedelta

import orjson as json
from django.conf import settings
from django.contrib.gis.geos import LineString
from django.core.serializers import serialize
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from tracking.api import CSVSerializer
from tracking.models import Device, LoggedPoint


class SpatialDataView(View):
    """Base view to return a queryset of spatial data as GeoJSON or CSV."""

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


class DeviceView(SpatialDataView):
    """Return structured data about tracking devices seen in the previous n days
    (14 by default).
    """

    model = Device
    geometry_field = "point"
    properties = (
        "age_colour",
        "age_minutes",
        "age_text",
        "altitude",
        "callsign",
        "deviceid",
        "heading",
        "icon",
        "id",
        "registration",
        "seen",
        "symbol",
        "velocity",
    )
    filename_prefix = "tracking_devices"

    def get_queryset(self):
        qs = super().get_queryset()

        if "days" in self.request.GET and self.request.GET["days"]:
            days = int(self.request.GET["days"])
        else:
            days = 14
        qs = qs.filter(seen__gte=timezone.now() - timedelta(days=days))

        # Querying on device callsign, registration and/or device ID.
        if "q" in self.request.GET and self.request.GET["q"]:
            query_str = self.request.GET["q"]
            qs = qs.filter()
            qs = qs.filter(
                Q(callsign__icontains=query_str)
                | Q(registration__icontains=query_str)
                | Q(deviceid__icontains=query_str)
            )

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
        """Override this method to return a linestring dataset instead of points."""
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
                setattr(
                    start_point,
                    "route",
                    LineString(start_point.point, loggedpoint.point),
                )
                start_label = start_point.seen.strftime("%H:%M:%S")
                end_label = loggedpoint.seen.strftime("%H:%M:%S")
                setattr(start_point, "label", f"{start_label} to {end_label}")
            start_point = loggedpoint

        # Exclude the last loggedpoint in the queryset because it won't have the `route` attribute.
        qs = qs[: len(qs) - 1]

        geojson = serialize(
            "geojson",
            qs,
            geometry_field="route",
            srid=self.srid,
            properties=(
                "id",
                "heading",
                "velocity",
                "altitude",
                "seen",
                "raw",
                "device_id",
                "label",
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


class ResourceMap(TemplateView):
    """A map view displaying all resource locations."""

    template_name = "tracking/resource_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "DBCA Resource Tracking System"
        context["geoserver_url"] = settings.GEOSERVER_URL
        return context


class DeviceDetailStream(View):
    """An experimental view that returns Server-Sent Events (SSE) consisting of
    a tracking device location, forever. This is a one-way communication channel,
    where the client browser is responsible for maintaining the connection.
    """

    async def stream(self, *args, **kwargs):
        """Returns an iterator that queries and then yields tracking device data every n seconds."""
        last_update = None
        device = None

        while True:
            # Run an asynchronous query for the specifed device.
            try:
                device = await Device.objects.aget(pk=kwargs["pk"])
                data = json.dumps(
                    {
                        "id": device.pk,
                        "deviceid": device.deviceid,
                        "seen": device.seen.isoformat(),
                        "point": device.point.ewkt,
                        "icon": device.icon,
                        "registration": device.registration,
                        "type": device.symbol,
                        "callsign": device.callsign,
                    }
                ).decode("utf-8")
            except:
                data = {}

            # Only send a message event if the device has been updated.
            if device and device.seen != last_update:
                last_update = device.seen
                yield f"data: {data}\n\n"
            else:
                # Always send a ping to keep the connection open.
                yield "event: ping\ndata: {}\n\n"

            # Sleep for a period before repeating.
            await asyncio.sleep(30)

    async def get(self, request, *args, **kwargs):
        return StreamingHttpResponse(
            self.stream(*args, **kwargs),
            content_type="text/event-stream",
            headers={
                # The Cache-Control header need to be set thus to work behind Fastly caching.
                "Cache-Control": "private, no-store",
                "Connection": "keep-alive",
            },
        )


class DeviceDetail(TemplateView):
    """Basic template view to test device streaming responses."""

    template_name = "tracking/device_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pk"] = kwargs["pk"]
        return context
