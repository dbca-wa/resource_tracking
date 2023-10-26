from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from mixer.backend.django import mixer
import random

from tracking.models import Device, LoggedPoint


class ViewTestCase(TestCase):

    def setUp(self):
        point = Point(random.uniform(32.0, 34.0), random.uniform(-115.0, -116.0))
        self.device = mixer.blend(Device, seen=timezone.now(), point=point)
        # Generate a short tracking history.
        mixer.blend(LoggedPoint, device=self.device, seen=self.device.seen, point=point)
        mixer.blend(LoggedPoint, device=self.device, seen=self.device.seen - timedelta(minutes=1), point=point)
        mixer.blend(LoggedPoint, device=self.device, seen=self.device.seen - timedelta(minutes=2), point=point)

        # Login
        self.client.force_login(User.objects.create(username='testuser'))

    def test_device_csv_download(self):
        """Test the devices.csv download view
        """
        url = reverse('track_device_csv')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_device_geojson_download(self):
        """Test the devices.geojson download view
        """
        url = reverse('track_device_geojson')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
