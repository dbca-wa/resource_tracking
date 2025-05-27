import asyncio
import re
from datetime import datetime, timedelta
from io import BytesIO

import orjson as json
import unicodecsv as csv
from django.conf import settings
from django.contrib.gis.geos import LineString, Polygon
from django.core.serializers import serialize
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View

from tracking.forms import DeviceForm
from tracking.models import SOURCE_DEVICE_TYPE_CHOICES, Device, LoggedPoint
from tracking.utils import get_next_pages, get_previous_pages

# Define a dictionary of context variables to supply to JavaScript in view templates.
# NOTE: we can't include values needing `reverse` in the dict below due to circular imports.
JAVASCRIPT_CONTEXT = {
    "geoserver_url": settings.GEOSERVER_URL,
    "car_icon_url": f"{settings.STATIC_URL}img/car.png",
    "ute_icon_url": f"{settings.STATIC_URL}img/4wd_ute.png",
    "light_unit_icon_url": f"{settings.STATIC_URL}img/light_unit.png",
    "gang_truck_icon_url": f"{settings.STATIC_URL}img/gang_truck.png",
    "comms_bus_icon_url": f"{settings.STATIC_URL}img/comms_bus.png",
    "rotary_aircraft_icon_url": f"{settings.STATIC_URL}img/rotary.png",
    "plane_icon_url": f"{settings.STATIC_URL}img/plane.png",
    "dozer_icon_url": f"{settings.STATIC_URL}img/dozer.png",
    "loader_icon_url": f"{settings.STATIC_URL}img/loader.png",
    "float_icon_url": f"{settings.STATIC_URL}img/float.png",
    "fuel_truck_icon_url": f"{settings.STATIC_URL}img/fuel_truck.png",
    "person_icon_url": f"{settings.STATIC_URL}img/person.png",
    "boat_icon_url": f"{settings.STATIC_URL}img/boat.png",
    "other_icon_url": f"{settings.STATIC_URL}img/other.png",
}


class DeviceMap(TemplateView):
    """A map view displaying all device locations."""

    template_name = "tracking/device_map.html"
    http_method_names = ["get", "head", "options"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "DBCA Resource Tracking device map"
        context["javascript_context"] = JAVASCRIPT_CONTEXT
        context["javascript_context"]["device_list_url"] = reverse("tracking:device_list")
        context["javascript_context"]["device_map_url"] = reverse("tracking:device_map")
        context["javascript_context"]["device_geojson_url"] = reverse("tracking:device_download")
        return context


class DeviceList(ListView):
    """A list view to display a list of tracking devices, and/or download them as structured data."""

    model = Device
    paginate_by = 20
    http_method_names = ["get", "head", "options"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "DBCA Resource Tracking device list"
        if self.request.GET.get("q", None):
            context["query_string"] = self.request.GET["q"]
        context["previous_pages"] = get_previous_pages(context["page_obj"])
        context["next_pages"] = get_next_pages(context["page_obj"])
        return context

    def get_queryset(self):
        qs = super().get_queryset()

        # Always filter out "hidden" devices.
        qs = qs.filter(hidden=False)

        # Optional filter to limit devices to those seen within the last n days.
        if self.request.GET.get("days", None):
            days = int(self.request.GET["days"])
            qs = qs.filter(seen__gte=timezone.now() - timedelta(days=days))

        # Querying on device callsign, registration and/or device ID.
        if self.request.GET.get("q", None):
            query_str = self.request.GET["q"]
            qs = qs.filter(
                Q(callsign__icontains=query_str)
                | Q(registration__icontains=query_str)
                | Q(deviceid__icontains=query_str)
                | Q(district__icontains=query_str)
            )

        return qs

    def get(self, request, *args, **kwargs):
        # Optionally, allow requests to this view to return a GeoJSON response.
        # Used by the device map view search.
        if self.request.GET.get("format", None) == "json":
            qs = self.get_queryset()
            geojson = serialize(
                "geojson",
                qs,
                geometry_field=DeviceDownload.geometry_field,
                srid=DeviceDownload.srid,
                properties=DeviceDownload.properties,
            )
            return HttpResponse(
                geojson,
                content_type="application/vnd.geo+json",
            )

        return super().get(request, *args, **kwargs)


class DeviceDetail(DetailView):
    """A detail view to show single device's details and location."""

    model = Device
    http_method_names = ["get", "head", "options"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["page_title"] = f"DBCA Resource Tracking device {obj.deviceid}"
        context["javascript_context"] = JAVASCRIPT_CONTEXT
        context["javascript_context"]["device_list_url"] = reverse("tracking:device_list")
        context["javascript_context"]["device_map_url"] = reverse("tracking:device_map")
        context["javascript_context"]["device_geojson_url"] = reverse("tracking:device_download")
        context["javascript_context"]["device_route_url"] = reverse("tracking:device_route", kwargs={"pk": obj.pk})
        context["javascript_context"]["event_source_url"] = reverse("tracking:device_stream", kwargs={"pk": obj.pk})
        return context


class DeviceUpdate(UpdateView):
    form_class = DeviceForm
    model = Device
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def dispatch(self, request, *args, **kwargs):
        """User authorisation checks occur here."""
        obj = self.get_object()
        # Check user authorisation (user has the required group and/or is a superuser).
        if not request.user.groups.filter(name=settings.DEVICE_EDITOR_USER_GROUP).exists() and not request.user.is_superuser:
            return HttpResponseForbidden(f"User updates to tracking device {obj.deviceid} are unauthorised.")
        # Check that the instance is user-editable (business rules on Device model).
        if not obj.user_editable():
            return HttpResponseForbidden(f"User updates to tracking device {obj.deviceid} are unauthorised.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["page_title"] = f"Update DBCA tracking device {obj.deviceid}"
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get("cancel", None):
            obj = self.get_object()
            return reverse("tracking:device_detail", kwargs={"pk": obj.pk})
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        obj = self.get_object()
        return reverse("tracking:device_detail", kwargs={"pk": obj.pk})


class SpatialDataView(View):
    """Base view to return a queryset of spatial data as GeoJSON or CSV."""

    model = None
    http_method_names = ["get", "head", "options"]
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

        # CSV format download.
        if self.format == "csv" or request.GET.get("format", None) == "csv":
            out = BytesIO()
            writer = csv.writer(out, quoting=csv.QUOTE_ALL)
            writer.writerow(
                [
                    "deviceid",
                    "registration",
                    "rin_number",
                    "rin_display",
                    "district",
                    "usual_driver",
                    "usual_location",
                    "current_driver",
                    "callsign",
                    "contractor_details",
                    "other_details",
                    "internal_only",
                    "hidden",
                    "fire_use",
                    "seen",
                    "point",
                    "heading",
                    "velocity",
                    "altitude",
                    "source_device_type",
                ]
            )
            for device in qs:
                writer.writerow(
                    [
                        device.deviceid,
                        device.registration,
                        device.rin_display,
                        device.rin_display,
                        device.get_district_display(),
                        device.usual_driver,
                        device.usual_location,
                        device.current_driver,
                        device.callsign,
                        device.contractor_details,
                        device.other_details,
                        device.internal_only,
                        device.hidden,
                        device.fire_use,
                        device.seen.astimezone(settings.TZ).strftime("%d/%b/%Y %H:%M:%S") if device.seen else None,
                        device.point.ewkt if device.point else None,
                        device.heading,
                        device.velocity,
                        device.altitude,
                        device.get_source_device_type_display(),
                    ]
                )
            out.seek(0)
            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f"{filename_prefix}_{timestamp}.csv"
            response = HttpResponse(
                out,
                content_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        # GeoJSON format download (default).
        else:
            geojson = serialize(
                "geojson",
                qs,
                geometry_field=self.geometry_field,
                srid=self.srid,
                properties=self.properties,
            )

            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f"{filename_prefix}_{timestamp}.json"
            response = HttpResponse(
                geojson,
                content_type="application/vnd.geo+json",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        return response


class DeviceDownload(SpatialDataView):
    """Return structured data about tracking devices."""

    model = Device
    geometry_field = "point"
    properties = (
        "id",
        "age_colour",
        "age_minutes",
        "age_text",
        "altitude",
        "callsign",
        "deviceid",
        "heading",
        "icon",
        "registration",
        "seen",
        "symbol",
        "velocity",
    )
    filename_prefix = "tracking_devices"

    def get_queryset(self):
        qs = super().get_queryset()

        # Always filter out "hidden" devices.
        qs = qs.filter(hidden=False)

        # Optional filter to limit devices to those seen within the last n days.
        if self.request.GET.get("days", None):
            days = int(self.request.GET["days"])
            qs = qs.filter(seen__gte=timezone.now() - timedelta(days=days))

        # Optional filter to limit devices seen within a given bounding box.
        # Expects a bbox param in the format <NE lat>,<NE lng>,<SW lat>,<SW lng>
        # i.e. the data returned from a Leaflet map.getBounds() call.
        # Example: 116.089,-31.879,115.650,-32.040
        if self.request.GET.get("bbox", None):
            # lat1, lng1, lat2, lng2
            pattern = re.compile(
                r"^(?P<lat1>[-+]?[0-9]*\.?[0-9]+),(?P<lng1>[-+]?[0-9]*\.?[0-9]+),(?P<lat2>[-+]?[0-9]*\.?[0-9]+),(?P<lng2>[-+]?[0-9]*\.?[0-9]+)$"
            )
            bbox_str = self.request.GET["bbox"]
            coords = pattern.match(bbox_str)
            if coords:  # Regex must return a full match.
                lat1 = float(coords.group("lat1"))
                lng1 = float(coords.group("lng1"))
                lat2 = float(coords.group("lat2"))
                lng2 = float(coords.group("lng2"))
                polygon = Polygon(((lng1, lat1), (lng1, lat2), (lng2, lat2), (lng2, lat1), (lng1, lat1)))
                qs = qs.filter(point__coveredby=polygon)

        # Querying on device callsign, registration and/or device ID.
        if self.request.GET.get("q", None):
            query_str = self.request.GET["q"]
            qs = qs.filter()
            qs = qs.filter(Q(callsign__icontains=query_str) | Q(registration__icontains=query_str) | Q(deviceid__icontains=query_str))

        return qs


class DeviceHistoryDownload(SpatialDataView):
    """Return structured data of the tracking points for a single device over the most-recent n days
    (14 by default).
    """

    model = LoggedPoint
    geometry_field = "point"
    properties = ("id", "heading", "velocity", "altitude", "seen", "device_id")

    def dispatch(self, *args, **kwargs):
        if "pk" not in self.kwargs:
            return HttpResponseBadRequest("Missing device PK")
        return super().dispatch(*args, **kwargs)

    def get_device(self):
        if not Device.objects.filter(pk=self.kwargs["pk"]).exists():
            return HttpResponseBadRequest("Unknown device")
        return Device.objects.get(pk=self.kwargs["pk"])

    def get_filename_prefix(self):
        device = self.get_device()
        return f"{device.deviceid}_loggedpoint"

    def get_queryset(self):
        qs = super().get_queryset()
        device = self.get_device()
        qs = qs.filter(device=device)

        start = self.request.GET.get("start", default=None)
        if start is None:
            # Use the date when the device was last seen.
            if device.seen:
                start = device.seen.date() - timedelta(days=14)
                start = datetime(start.year, start.month, start.day, 0, 0).astimezone(settings.TZ)
            else:
                start = timezone.now() - timedelta(days=14)
        else:
            try:
                # Parse the start date as ISO8601 date format
                start = datetime.fromisoformat(start)
            except:
                return HttpResponseBadRequest("Bad start format, use ISO 8601 format start parameter")
        qs = qs.filter(seen__gte=start)

        end = self.request.GET.get("end", default=None)
        if end is not None:
            try:
                # Parse the end date as ISO8601 date format
                end = datetime.fromisoformat(start)
            except:
                return HttpResponseBadRequest("Bad end format, use ISO 8601 format end parameter")

            qs = qs.filter(seen__lt=end)

        return qs

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        filename_prefix = self.get_filename_prefix()

        # CSV format download.
        if self.format == "csv" or request.GET.get("format", None) == "csv":
            out = BytesIO()
            writer = csv.writer(out, quoting=csv.QUOTE_ALL)
            writer.writerow(["id", "heading", "velocity", "altitude", "seen", "device_id"])
            for loggedpoint in qs:
                writer.writerow(
                    [
                        loggedpoint.id,
                        loggedpoint.heading,
                        loggedpoint.velocity,
                        loggedpoint.altitude,
                        loggedpoint.seen.astimezone(settings.TZ).strftime("%d/%b/%Y %H:%M:%S"),
                        loggedpoint.device,
                    ]
                )
            out.seek(0)
            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f"{filename_prefix}_{timestamp}.csv"
            response = HttpResponse(
                out,
                content_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        # GeoJSON format download (default).
        else:
            geojson = serialize(
                "geojson",
                qs,
                geometry_field=self.geometry_field,
                srid=self.srid,
                properties=self.properties,
            )

            timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
            filename = f"{filename_prefix}_{timestamp}.json"
            response = HttpResponse(
                geojson,
                content_type="application/vnd.geo+json",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        return response


class DeviceRouteDownload(DeviceHistoryDownload):
    """Extend the DeviceHistoryDownload view to return a device's route history as a LineString geometry.
    This view only returns GeoJSON, not CSV.
    """

    properties = (
        "id",
        "heading",
        "velocity",
        "altitude",
        "seen",
        "device_id",
        "label",
    )
    geometry_field = "route"

    def get(self, request, *args, **kwargs):
        """Override this method to return a linestring dataset instead of points."""
        qs = self.get_queryset()
        device = self.get_device()
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
        if qs:
            qs = qs[: len(qs) - 1]

        geojson = serialize(
            "geojson",
            qs,
            geometry_field=self.geometry_field,
            srid=self.srid,
            properties=self.properties,
        )
        timestamp = datetime.strftime(datetime.today(), "%Y-%m-%d_%H%M")
        filename = f"{filename_prefix}_{timestamp}.json"
        response = HttpResponse(
            geojson,
            content_type="application/vnd.geo+json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

        return response


class DeviceStream(View):
    """An asynchronous view that returns Server-Sent Events (SSE) consisting of
    a tracking device's location, forever. This is a one-way communication channel,
    where the client browser is responsible for maintaining the connection.
    """

    http_method_names = ["get"]
    view_is_async = True

    async def stream(self, *args, **kwargs):
        """Returns an iterator that queries and then yields tracking device data every n seconds."""
        last_location = None
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
                        "type": device.get_symbol_display(),
                        "callsign": device.callsign,
                        "symbol": device.symbol,
                        "age_text": device.age_text,
                    }
                ).decode("utf-8")
            except:
                data = {}

            # Only send a message event if the device location has changed.
            # Include a recommended retry delay for reconnections of 15000 ms.
            # Reference: https://javascript.info/server-sent-events
            if device and device.point.ewkt != last_location:
                last_location = device.point.ewkt
                yield f"event: message\nretry: 15000\ndata: {data}\nid: {int(device.seen.timestamp())}\n\n"
            else:
                # Always send a ping to keep the connection open.
                yield "event: ping\nretry: 15000\ndata: {}\n\n"

            # Sleep for a period before repeating.
            await asyncio.sleep(10)

    async def get(self, request, *args, **kwargs):
        # Returns a streaming HTTP response that is consumed by the EventSource instance on the client.
        return StreamingHttpResponse(
            self.stream(*args, **kwargs),
            content_type="text/event-stream",
            headers={
                # The Cache-Control header need to be set thus to work behind Fastly caching.
                "Cache-Control": "private, no-store",
                "Connection": "keep-alive",
            },
        )


class DeviceMetricsSource(View):
    """A basic metrics view that returns the count of logged points for a given source device type
    over the previous n minutes."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        source_device_type = kwargs["source_device_type"]
        # Basic validation of the source device type.
        if source_device_type not in [i[0] for i in SOURCE_DEVICE_TYPE_CHOICES]:
            return HttpResponseBadRequest("Bad request")

        if request.GET.get("minutes", None):
            try:
                minutes = int(request.GET["minutes"])
            except ValueError:
                return HttpResponseBadRequest("Bad request")
            # Maximum duration considered is 24h, minimum is 1 minute.
            if minutes > 1440 or minutes < 1:
                return HttpResponseBadRequest("Bad request")
        else:
            # Default to the previous 15 minutes.
            minutes = 15

        since = timezone.now() - timedelta(minutes=minutes)
        logged_point_count = LoggedPoint.objects.filter(seen__gte=since, source_device_type=source_device_type).count()
        source_device_type_display = source_device_type
        for i in SOURCE_DEVICE_TYPE_CHOICES:
            if source_device_type == i[0]:
                source_device_type_display = i[1]
                break

        return JsonResponse(
            {
                "timestamp": timezone.now(),
                "source_device_type": source_device_type_display,
                "minutes": minutes,
                "logged_point_count": logged_point_count,
            }
        )
