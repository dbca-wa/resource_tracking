import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from mixer.backend.django import mixer

from tracking.models import Device, LoggedPoint


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
        url = reverse("device_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_download(self):
        """Test the devices download view returns JSON"""
        url = reverse("device_download")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/vnd.geo+json")

    def test_device_csv_download(self):
        """Test the devices download view returns CSV"""
        url = reverse("device_download")
        response = self.client.get(url + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/csv")

    def test_device_map_view(self):
        """Test the device map view"""
        url = reverse("device_map")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_detail_view(self):
        """Test the device detail view"""
        url = reverse("device_detail", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_history_geojson_view(self):
        """Test the device history GeoJSON view"""
        url = reverse("device_history", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/vnd.geo+json")

    def test_device_history_csv_view(self):
        """Test the device history CSV view"""
        url = reverse("device_history", kwargs={"pk": self.device.pk})
        response = self.client.get(url + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/csv")

    def test_device_route_geojson_view(self):
        """Test the device route GeoJSON view"""
        url = reverse("device_route", kwargs={"pk": self.device.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/vnd.geo+json")

    def test_device_metrics_source(self):
        """Test the device metrics view"""
        url = reverse("device_metrics_source", kwargs={"source_device_type": self.device.source_device_type})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
