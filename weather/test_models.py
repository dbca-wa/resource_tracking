from __future__ import absolute_import, unicode_literals
from datetime import timedelta
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from mixer.backend.django import mixer
import random

from .models import Location, WeatherStation, WeatherObservation


# TODO: obtain a list of 5-10 strings for each model, containing any minor
# variations that might occur.
TELVENT_DATA = [
    'VP=1|STN=900002|UTC=20161223043700|T=38.5|TN=38.3|TX=38.7|TS=0.1|TQ=60|W=38.4|WN=37.9|WX=38.7|WS=0.2|WQ=60|QFE=923.0|QFES=0.0|QFEQ=60|H=24|HN=24|HX=24|HS=0|HQ=60|D=162|DS=13|DQ=60|S=13.145|SN=9.2|SX=18.1|SS=2.6|SQ=60|R=400.8|RQ=60|VER=1.00|BV=13.8|ET=43.5|SSS=01004|MN=341|EC=89',
    'NVP=1|STN=900002|UTC=20161223052800|T=23.4|TN=23.4|TX=23.5|TS=0.0|TQ=60|W=23.0|WN=23.0|WX=23.1|WS=0.0|WQ=60|QFE=968.6|QFES=0.0|QFEQ=60|H=98|HN=98|HX=98|HS=0|HQ=60|D=18|DS=15|DQ=60|S=9.021|SN=6.6|SX=12.4|SS=1.4|SQ=60|R=933.6|RQ=60|VER=1.00|BV=12.8|ET=27.3|SSS=02004|MN=2894|EC=7949',
]
VAISALA_DATA = [
    '0R0,Dn=125D,Dm=162D,Dx=180D,Sn=2.7N,Sm=3.7N,Sx=5.1N,Ta=21.0C,Tp=22.1C,Ua=45.7P,Pa=966.2H,Rc=0.07M,Rd=340s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M,Rp=1.4M,Hp=0.0M,Tr=72.4C,Ra=0.0M,Sl=0.001075V,Sr=-0.546963V,Rt=1280.0R,Vs=13.4V',
    '0r0,Dn=200D,Dm=279D,Dx=319D,Sn=1.3N,Sm=5.3N,Sx=7.7N,Ta=25.6C,Tp=26.0C,Ua=29.4P,Pa=960.7H,Rc=0.15M,Rd=420s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M,Rp=1.9M,Hp=0.0M,Tr=292.2C,Ra=0.0M,Sl=0.001158V,Sr=-0.016761V,Rt=2965.0R,Vs=13.2V',
]


class WeatherTestCase(TestCase):

    def setUp(self):
        # Generate one of each type of weather station.
        p = Point(random.randrange(-180, 180), random.randrange(-180, 180))
        self.telvent = mixer.blend(
            WeatherStation, manufacturer='telvent', location=mixer.blend(Location, point=p))
        p = Point(random.randrange(-180, 180), random.randrange(-180, 180))
        self.vaisala = mixer.blend(
            WeatherStation, manufacturer='vaisala', location=mixer.blend(Location, point=p))


class WeatherStationTestCase(WeatherTestCase):

    def test_save_observation(self):
        """Test the WeatherStation save_observation method
        """
        for k, data in enumerate(TELVENT_DATA):
            timestamp = timezone.now() - timedelta(hours=k)
            obs = self.telvent.save_observation(data, timestamp)
            self.assertTrue(isinstance(obs, WeatherObservation))
        for k, data in enumerate(VAISALA_DATA):
            timestamp = timezone.now() - timedelta(hours=k)
            obs = self.vaisala.save_observation(data, timestamp)
            self.assertTrue(isinstance(obs, WeatherObservation))


class WeatherObservationTestCase(WeatherTestCase):

    def test_get_dafwa_obs(self):
        """Test the WeatherObservation get_dafwa_obs method
        """
        for k, data in enumerate(TELVENT_DATA):
            timestamp = timezone.now() - timedelta(hours=k)
            obs = self.telvent.save_observation(data, timestamp)
            dafwa_obs = obs.get_dafwa_obs()
            self.assertTrue(isinstance(dafwa_obs, list))
            # Each element in the list should be a string.
            for i in dafwa_obs:
                self.assertTrue(isinstance(i, unicode))
        for k, data in enumerate(VAISALA_DATA):
            timestamp = timezone.now() - timedelta(hours=k)
            obs = self.vaisala.save_observation(data, timestamp)
            dafwa_obs = obs.get_dafwa_obs()
            self.assertTrue(isinstance(dafwa_obs, list))
            for i in dafwa_obs:
                self.assertTrue(isinstance(i, unicode))
