from __future__ import absolute_import, unicode_literals
from django.contrib.gis.geos import Point
from django.test import TestCase
from mixer.backend.django import mixer
import random

from .models import Location, WeatherStation, WeatherObservation


# TODO: obtain a list of 5-10 strings for each model, containing any minor
# variations that might occur.
TELVENT_DATA = [
    'VP=1|STN=900002|UTC=20161223043700|T=38.5|TN=38.3|TX=38.7|TS=0.1|TQ=60|W=38.4|WN=37.9|WX=38.7|WS=0.2|WQ=60|QFE=923.0|QFES=0.0|QFEQ=60|H=24|HN=24|HX=24|HS=0|HQ=60|D=162|DS=13|DQ=60|S=13.145|SN=9.2|SX=18.1|SS=2.6|SQ=60|R=400.8|RQ=60|VER=1.00|BV=13.8|ET=43.5|SSS=01004|MN=341|EC=89',
    'NVP=1|STN=900002|UTC=20161223052800|T=23.4|TN=23.4|TX=23.5|TS=0.0|TQ=60|W=23.0|WN=23.0|WX=23.1|WS=0.0|WQ=60|QFE=968.6|QFES=0.0|QFEQ=60|H=98|HN=98|HX=98|HS=0|HQ=60|D=18|DS=15|DQ=60|S=9.021|SN=6.6|SX=12.4|SS=1.4|SQ=60|R=933.6|RQ=60|VER=1.00|BV=12.8|ET=27.3|SSS=02004|MN=2894|EC=7949',
    '10.3.15.105::NVP=1|STN=900003|UTC=20171129065921|T=20.3|TN=20.1|TX=20.4|TS=00|TQ=00|W=00|WN=00|WX=00|WS=00|WQ=00|QFE=976.2|QFES=00|QFEQ=00|QNH=1013.0|H=35|HN=35|HX=36|HS=00|HQ=00|D=197|DS=00|DQ=00|S=10.096|SN=8.5|SX=12.1|SS=00|SQ=00|R=126.4|RQ=00|VER=1.00|BV=13.6|ET=32.6|SSS=00|MN=00|EC=00|Date=2017-11-29|Time=12:59:21|Site=ROGR',
    '10.201.15.105::NVP=1|STN=900003|UTC=20171129065958|T=36.9|TN=36.6|TX=37.1|TS=00|TQ=00|W=00|WN=00|WX=00|WS=00|WQ=00|QFE=927.5|QFES=00|QFEQ=00|QNH=1000.6|H=13|HN=13|HX=13|HS=00|HQ=00|D=298|DS=00|DQ=00|S=13.152|SN=9.9|SX=17.9|SS=00|SQ=00|R=6.0|RQ=00|VER=1.00|BV=13.7|ET=48.2|SSS=00|MN=00|EC=00|Date=2017-11-30|Time=14:59:58|Site=KARI',
]
VAISALA_DATA = [
    '0R0,Dn=125D,Dm=162D,Dx=180D,Sn=2.7N,Sm=3.7N,Sx=5.1N,Ta=21.0C,Tp=22.1C,Ua=45.7P,Pa=966.2H,Rc=0.07M,Rd=340s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M,Rp=1.4M,Hp=0.0M,Tr=72.4C,Ra=0.0M,Sl=0.001075V,Sr=-0.546963V,Rt=1280.0R,Vs=13.4V',
    '0r0,Dn=200D,Dm=279D,Dx=319D,Sn=1.3N,Sm=5.3N,Sx=7.7N,Ta=25.6C,Tp=26.0C,Ua=29.4P,Pa=960.7H,Rc=0.15M,Rd=420s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M,Rp=1.9M,Hp=0.0M,Tr=292.2C,Ra=0.0M,Sl=0.001158V,Sr=-0.016761V,Rt=2965.0R,Vs=13.2V',
    '10.3.27.105::0R0,Dn=192D,Dm=215D,Dx=238D,Sn=9.2N,Sm=13.7N,Sx=18.1N,Ta=15.8C,Tp=0.0C,Ua=51.2P,Pa=974.1H,Pq=1008.6H,Rc=0.00M,Rf=0.00M,Rd=0s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M,Rp=0.0M,Hp=0.0M,Tr=0.0C,Ra=0.0M,Vs=13.6V,Date=2017-11-29,Time=12:00:10,Site=YERR',
    '10.3.26.105::0R0,Dn=180D,Dm=206D,Dx=239D,Sn=1.4N,Sm=7.1N,Sx=9.2N,Ta=13.5C,Tp=0.0C,Ua=47.8P,Pa=944.5H,Pq=1012.8H,Rc=0.00M,Rf=0.00M,Rd=0s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M,Rp=0.0M,Hp=0.0M,Tr=0.0C,Ra=0.0M,Vs=13.9V,Date=2017-11-30,Time=15:00:10,Site=SOLS',
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
            obs = self.telvent.save_observation(data)
            self.assertTrue(isinstance(obs, WeatherObservation))
        for k, data in enumerate(VAISALA_DATA):
            obs = self.vaisala.save_observation(data)
            self.assertTrue(isinstance(obs, WeatherObservation))


class WeatherObservationTestCase(WeatherTestCase):

    def test_get_dafwa_obs(self):
        """Test the WeatherObservation get_dafwa_obs method
        """
        for k, data in enumerate(TELVENT_DATA):
            obs = self.telvent.save_observation(data)
            dafwa_obs = obs.get_dafwa_obs()
            self.assertTrue(isinstance(dafwa_obs, list))
            # Each element in the list should be a string.
            for i in dafwa_obs:
                self.assertTrue(isinstance(i, unicode))
        for k, data in enumerate(VAISALA_DATA):
            obs = self.vaisala.save_observation(data)
            dafwa_obs = obs.get_dafwa_obs()
            self.assertTrue(isinstance(dafwa_obs, list))
            for i in dafwa_obs:
                self.assertTrue(isinstance(i, unicode))
