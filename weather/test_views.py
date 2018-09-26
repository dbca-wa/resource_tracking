from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.test import TestCase, Client
from mixer.backend.django import mixer
from .models import WeatherStation, WeatherObservation


class WeatherViewsTestCase(TestCase):
    client = Client()

    def setUp(self):
        # We need a defined Group, because of the user_post_save signal in
        # the tracking app.
        Group.objects.create(name='Edit Resource Tracking Device')
        # Create User object.
        self.user1 = User.objects.create_user(
            username='testuser', email='test@email.com')
        self.user1.set_password('pass')
        self.user1.save()
        # Log in user1 by default.
        self.client.login(username=self.user1.username, password='pass')
        # Create a WeatherStation object.
        self.ws = mixer.blend(WeatherStation)
        mixer.cycle(5).blend(WeatherObservation, station=self.ws)

    def test_get_index(self):
        """Test index GET response
        """
        url = reverse('weather_index')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_get_weatherstation(self):
        """Test weatherstation GET response
        """
        url = reverse('weather_station', kwargs={'station_id': self.ws.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_get_observations_health(self):
        """Test observations_health GET response
        """
        url = reverse('observations_health')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
