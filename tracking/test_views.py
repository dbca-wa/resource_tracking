import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from mixer.backend.django import mixer

from tracking.models import Device, LoggedPoint
from tracking.views import PRTG_DEVICE_TYPES


class ViewTestCase(TestCase):
    def setUp(self):
        point = Point(random.uniform(32.0, 34.0), random.uniform(-115.0, -116.0))
        self.device = mixer.blend(Device, seen=timezone.now(), point=point)
        mixer.blend(LoggedPoint, device=self.device, seen=self.device.seen, point=point)
        # Generate a short tracking history.
        for i in range(1, 5):
            point.x = point.x + random.uniform(-0.01, 0.01)
            point.y = point.y + random.uniform(-0.01, 0.01)
            mixer.blend(LoggedPoint, device=self.device, seen=self.device.seen - timedelta(minutes=i), point=point)
        # Login
        self.client.force_login(User.objects.create(username="testuser"))

    def test_device_list_view(self):
        """Test the device list view"""
        url = reverse("tracking:device_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_geojson(self):
        """Test the devices download view returns GeoJSON"""
        url = reverse("tracking:device_download")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/vnd.geo+json")

    def test_device_csv_download(self):
        """Test the devices download view returns CSV"""
        url = reverse("tracking:device_download")
        response = self.client.get(url + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/csv")

    def test_device_gpkg_download(self):
        """Test the devices download view returns GPKG"""
        url = reverse("tracking:device_download")
        response = self.client.get(url + "?format=gpkg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/x-sqlite3")

    def test_device_map_view(self):
        """Test the device map view"""
        url = reverse("tracking:device_map")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_detail_view(self):
        """Test the device detail view"""
        url = reverse("tracking:device_detail", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_history_geojson_view(self):
        """Test the device history GeoJSON view"""
        url = reverse("tracking:device_history", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/vnd.geo+json")

    def test_device_history_csv_view(self):
        """Test the device history CSV view"""
        url = reverse("tracking:device_history", kwargs={"pk": self.device.pk})
        response = self.client.get(url + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/csv")

    def test_device_history_gpkg_view(self):
        """Test the device history GPKG view"""
        url = reverse("tracking:device_history", kwargs={"pk": self.device.pk})
        response = self.client.get(url + "?format=gpkg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/x-sqlite3")

    def test_device_route_geojson_view(self):
        """Test the device route GeoJSON view"""
        url = reverse("tracking:device_route", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/vnd.geo+json")

    def test_device_route_gpkg_view(self):
        """Test the device route GPKG view"""
        url = reverse("tracking:device_route", kwargs={"pk": self.device.pk})
        response = self.client.get(url + "?format=gpkg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/x-sqlite3")

    def test_device_metrics_source(self):
        """Test the device metrics view"""
        url = reverse("tracking:device_metrics_source", kwargs={"source_device_type": self.device.source_device_type})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")


class PrtgMetricsViewTestCase(TestCase):
    def setUp(self):
        # `cache_page` responses persist in the test cache, so clear it between tests.
        cache.clear()
        self.url = reverse("prtg_metrics_json")
        self.client.force_login(User.objects.create(username="testuser"))
        self.point = Point(random.uniform(32.0, 34.0), random.uniform(-115.0, -116.0))
        self.device = mixer.blend(Device, seen=timezone.now(), point=self.point, source_device_type="tracplus")
        self.seen = timezone.now() - timedelta(minutes=5)
        mixer.blend(LoggedPoint, device=self.device, seen=self.seen, point=self.point, source_device_type="tracplus")

    def get_channels(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        return {channel["channel"]: channel for channel in response.json()["prtg"]["result"]}

    def test_prtg_metrics_json(self):
        """Test the PRTG metrics view returns a channel per tracked device type"""
        channels = self.get_channels(self.client.get(self.url))
        # Two "all devices" channels, plus a delay and rate channel per tracked device type.
        self.assertEqual(len(channels), 2 + (2 * len(PRTG_DEVICE_TYPES)))
        self.assertEqual(channels["All tracking devices delay"]["value"], 5)
        self.assertEqual(channels["All tracking devices logging rate"]["value"], int(1 / 15))
        self.assertEqual(channels["TracPlus tracking devices delay"]["value"], 5)
        self.assertEqual(channels["TracPlus logging rate"]["value"], int(1 / 15))
        # Device types without any logged points in the period report an error.
        self.assertEqual(channels["DFES tracking devices delay"]["error"], 1)
        self.assertEqual(channels["DFES logging rate"]["value"], 0)
        self.assertNotIn("error", channels["TracPlus tracking devices delay"])

    def test_prtg_metrics_ignores_future_points(self):
        """Test that logged points with a future `seen` value are ignored"""
        mixer.blend(
            LoggedPoint,
            device=self.device,
            seen=timezone.now() + timedelta(days=1),
            point=self.point,
            source_device_type="spot",
        )
        channels = self.get_channels(self.client.get(self.url))
        self.assertEqual(channels["All tracking devices delay"]["value"], 5)
        # The future point is excluded, so Spot has no usable data in the period.
        self.assertEqual(channels["Spot tracking devices delay"]["value"], 0)
        self.assertEqual(channels["Spot tracking devices delay"]["error"], 1)

    def test_prtg_metrics_stale_device_type(self):
        """Test that a device type last seen outside the metrics period reports no data"""
        other_device = mixer.blend(Device, seen=timezone.now(), point=self.point, source_device_type="dfes")
        mixer.blend(
            LoggedPoint,
            device=other_device,
            seen=timezone.now() - timedelta(days=30),
            point=self.point,
            source_device_type="dfes",
        )
        channels = self.get_channels(self.client.get(self.url))
        self.assertEqual(channels["DFES tracking devices delay"]["value"], 0)
        self.assertEqual(channels["DFES tracking devices delay"]["error"], 1)

    def test_prtg_metrics_query_count(self):
        """Test that the metrics view issues bounded queries rather than aggregating over the period"""
        with CaptureQueriesContext(connection) as context:
            self.client.get(self.url)
        loggedpoint_queries = [query["sql"] for query in context.captured_queries if "tracking_loggedpoint" in query["sql"]]
        # One lookup for the newest point overall, one per tracked device type, and one count of logging rate.
        self.assertEqual(len(loggedpoint_queries), 1 + len(PRTG_DEVICE_TYPES) + 1)
        # The "newest point" lookups must not aggregate over every point in the period.
        self.assertFalse(any("GROUP BY" in sql and "MAX(" in sql.upper() for sql in loggedpoint_queries))

    def test_prtg_metrics_requires_login(self):
        """Test the metrics view requires an authenticated user"""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/admin/"))
