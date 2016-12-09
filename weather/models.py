# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from datetime import timedelta, time, datetime
from django.conf import settings
from django.contrib.gis.db import models
from django.db.models import Max, Min
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
import logging
import math
import pytz
import re
import telnetlib

from weather.utils import dew_point, actual_pressure, actual_rainfall


logger = logging.getLogger('weather')
KNOTS_TO_MS = Decimal('0.51444')
KNOTS_TO_KS = Decimal('1.85166')
TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@python_2_unicode_compatible
class Location(models.Model):
    """Represents the location of a weather station.
    """
    title = models.CharField(blank=True, max_length=128)
    description = models.TextField(blank=True)
    point = models.PointField()
    height = models.DecimalField(max_digits=7, decimal_places=3)

    def __str__(self):
        return force_text('{} {}'.format(self.title, self.point.tuple))


@python_2_unicode_compatible
class WeatherStation(models.Model):
    """Represents an automatic weather station (AWS) installation.
    """
    MANUFACTURER_CHOICES = (
        ('telvent', 'Telvent'),
        ('vaisala', 'Vaisala'),
    )
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, null=True, blank=True)
    abbreviation = models.CharField(max_length=20)
    bom_abbreviation = models.CharField(max_length=4)
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField(default=43000)
    last_scheduled = models.DateTimeField()
    last_reading = models.DateTimeField()
    battery_voltage = models.DecimalField(max_digits=3, decimal_places=1)
    connect_every = models.PositiveSmallIntegerField(default=15)
    active = models.BooleanField(default=False)
    stay_connected = models.BooleanField(
        default=False, verbose_name='Persistent connection')
    manufacturer = models.CharField(
        max_length=100, null=True, blank=True, choices=MANUFACTURER_CHOICES)

    class Meta:
        ordering = ['-last_reading']

    def last_reading_local(self):
        """Return the datetime of the latest reading, offset to local time.
        """
        return self.last_reading.astimezone(TIMEZONE)

    def last_reading_time(self):
        """Reading local time of latest reading in 24h time (HHMM).
        """
        return datetime.strftime(self.last_reading_local(), '%H%M')

    def rain_since_nine_am(self):
        now = timezone.make_aware(datetime.now(), TIMEZONE)

        if now.time() > time(9):
            last_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            yesterday = now - timedelta(hours=24)
            last_9am = yesterday.replace(hour=9, minute=0, second=0, microsecond=0)
        try:
            rainfall_stats = self.readings.filter(rainfall__gt=0, date__gte=last_9am).aggregate(Min('rainfall'), Max('rainfall'))
            return rainfall_stats['rainfall__max'] - rainfall_stats['rainfall__min']
        except:
            return 0

    def download_observation(self):
        """Utility function to connect to an AWS via Telnet and download a
        single observation.
        """
        retrieval_time = timezone.now().replace(microsecond=0)
        logger.info("Trying to connect to {}".format(self.name))
        client, output = None, False
        try:
            client = telnetlib.Telnet(self.ip_address, self.port)
            if self.manufacturer == 'vaisala':
                pattern = '(\\r\\n)(0R0.+V)(\\r\\n)'
                clean_response = False
                while not clean_response:
                    response = client.read_until('V\r\n'.encode('utf8'), 60)
                    m = re.search(pattern, response)
                    if m:
                        response = m.group(2)
                        clean_response = True
            else:  # Default to using the Telvent station format.
                response = client.read_until('\r\n'.encode('utf8'), 60)
                response = response[2:]
            if client:
                client.close()
        except Exception as e:
            logger.error('Failed to read weather data from {}'.format(self.name))
            logger.exception(e)
            return None

        logger.info("PERIODIC READING OF {}".format(self.name))
        logger.info(force_text(response))
        output = (self.pk, force_text(response), retrieval_time)
        return output

    def save_weather_data(self, raw_data, last_reading=None):
        """
        Convert NVP format to django record
        """
        if last_reading is None:
            last_reading = timezone.now()
        EMPTY = Decimal('0.00')

        # Create a weather reading.from the retrieved data.
        if self.manufacturer == 'vaisala':
            # Vaisala data is a comma-separated NVP format.
            items = raw_data.split(',')
            items.pop(0)  # Remove the first element of the raw data.
            data = {}
            for item in items:
                k, v = item.split('=')
                data[k] = v
            reading = WeatherObservation()
            reading.temperature = Decimal(data.get('Ta')[:-1])
            reading.humidity = Decimal(data.get('Ua')[:-1])
            reading.dew_point = dew_point(float(reading.temperature),
                                          float(reading.humidity))
            reading.pressure = Decimal(data.get('Pa')[:-1])
            reading.wind_direction_min = Decimal(data.get('Dn')[:-1])
            reading.wind_direction_max = Decimal(data.get('Dx')[:-1])
            reading.wind_direction = Decimal(data.get('Dm')[:-1])
            reading.wind_speed_min = Decimal(data.get('Sn')[:-1]) * KNOTS_TO_MS
            reading.wind_speed_min_kn = Decimal(data.get('Sn')[:-1])
            reading.wind_speed_max = Decimal(data.get('Sx')[:-1]) * KNOTS_TO_MS
            reading.wind_speed_max_kn = Decimal(data.get('Sx')[:-1])
            reading.wind_speed = Decimal(data.get('Sm')[:-1]) * KNOTS_TO_MS
            reading.wind_speed_kn = Decimal(data.get('Sm')[:-1])
            reading.rainfall = Decimal(data.get('Rc')[:-1])
            reading.actual_rainfall = actual_rainfall(Decimal(reading.rainfall),
                                                      self, last_reading)
            reading.actual_pressure = actual_pressure(float(reading.temperature),
                                                      float(reading.pressure),
                                                      float(self.location.height))
            reading.raw_data = raw_data
            reading.station = self
            reading.save()
            self.last_reading = last_reading
            self.battery_voltage = Decimal(data.get('Vs')[:-1])
            self.save()
        else:  # Default to using the Telvent station format.
            # Telvent data is stored in NVP format separated by the pipe symbol '|'.
            #   |<NAME>=<VALUE>|
            items = raw_data.split('|')
            data = {}
            for item in items:
                if (item != ''):
                    try:
                        k, v = item.split('=')
                        data[k] = v
                    except:
                        pass

            reading = WeatherObservation()
            reading.temperature_min = data.get('TN') or EMPTY
            reading.temperature_max = data.get('TX') or EMPTY
            reading.temperature = data.get('T') or EMPTY
            reading.temperature_deviation = data.get('TS') or EMPTY
            reading.temperature_outliers = data.get('TO') or 0
            reading.pressure_min = data.get('QFEN') or EMPTY
            reading.pressure_max = data.get('QFEX') or EMPTY
            reading.pressure = data.get('QFE') or EMPTY
            reading.pressure_deviation = data.get('QFES') or EMPTY
            reading.pressure_outliers = data.get('QFEO') or 0
            reading.humidity_min = data.get('HN') or EMPTY
            reading.humidity_max = data.get('HX') or EMPTY
            reading.humidity = data.get('H') or EMPTY
            reading.humidity_deviation = data.get('HS') or EMPTY
            reading.humidity_outliers = data.get('HO') or 0
            reading.wind_direction_min = data.get('DN') or EMPTY
            reading.wind_direction_max = data.get('DX') or EMPTY
            reading.wind_direction = data.get('D') or EMPTY
            reading.wind_direction_deviation = data.get('DS') or EMPTY
            reading.wind_direction_outliers = data.get('DO') or 0
            if (data.get('SN')):
                reading.wind_speed_min = Decimal(data.get('SN')) * KNOTS_TO_MS or 0
                reading.wind_speed_min_kn = Decimal(data.get('SN')) or 0
                reading.wind_speed_deviation = Decimal(data.get('SS')) * KNOTS_TO_MS or 0
                reading.wind_speed_outliers = data.get('SO') or 0
                reading.wind_speed_deviation_kn = Decimal(data.get('SS')) or 0
            if (data.get('SX')):
                reading.wind_speed_max = Decimal(data.get('SX')) * KNOTS_TO_MS or 0
                reading.wind_speed_max_kn = Decimal(data.get('SX')) or 0
            if (data.get('S')):
                reading.wind_speed = Decimal(data.get('S')) * KNOTS_TO_MS or 0
                reading.wind_speed_kn = Decimal(data.get('S')) or 0
            reading.rainfall = data.get('R') or EMPTY
            reading.dew_point = dew_point(float(reading.temperature),
                                          float(reading.humidity))
            reading.actual_rainfall = actual_rainfall(Decimal(reading.rainfall),
                                                      self, last_reading)
            reading.actual_pressure = actual_pressure(float(reading.temperature),
                                                      float(reading.pressure),
                                                      float(self.location.height))
            reading.raw_data = raw_data
            reading.station = self
            reading.save()
            self.last_reading = last_reading
            self.battery_voltage = data.get('BV', EMPTY) or EMPTY
            self.save()

        return reading

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class WeatherObservation(models.Model):
    """Represents an observation of weather from an AWS.

    Capable of storing information from a NVP messsage about the following
    (one minute unless otherwise specified):
        Air temperature in degrees Celsius
            - instantaneous (TI), average (T), minimum (TN), maximum (TX),
              standard deviation (TS), number of outliers (TO), quality (TQ).
        Wet bulb temperature in degrees Celsius
            - instantaneous (WI), average (W), minimum (WN), maximum (WX),
              standard deviation (WS), number of outliers (WS), quality (WQ).
        Station-level atmospheric pressure in hectopascals (not sea-level
        adjusted)
            - instantaneous (QFEI), average (QFE), minimum (QFEN),
              maximum (QFEX), standard deviation (QFES),
              number of outliers (QFEO), quality (QFEQ)
        Relative humidity in percent
            - instantaneous (HI), average (H), minimum (HN), maximum (HX),
              standard deviation (HS), number of outliers (HO), quality (HQ)
        Wind direction in degrees from North
            - instantaneous (DI), average (D), minimum (DN), maximum (DX),
              standard deviation (DS), number of outliers (DO), quality (DQ)
        Wind speed in kilometres per hour
            - instantaneous (SI), average (S), minimum (SN), maximum (SX),
              standard deviation (SS), number of outliers (SO), quality (SQ)
        Rainfall in millimetres
            - total (R)
    """
    station = models.ForeignKey(WeatherStation, related_name='readings')
    date = models.DateTimeField(default=timezone.now)
    raw_data = models.TextField()

    temperature_min = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    temperature_max = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True,
        help_text='Temperature (°Celcius)')
    temperature_deviation = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    temperature_outliers = models.PositiveIntegerField(
        blank=True, null=True)

    pressure_min = models.DecimalField(
        max_digits=5, decimal_places=1, blank=True, null=True)
    pressure_max = models.DecimalField(
        max_digits=5, decimal_places=1, blank=True, null=True)
    pressure = models.DecimalField(
        max_digits=5, decimal_places=1, blank=True, null=True,
        help_text='Pressure (hPa)')
    pressure_deviation = models.DecimalField(
        max_digits=5, decimal_places=1, blank=True, null=True)
    pressure_outliers = models.PositiveIntegerField(
        blank=True, null=True)

    humidity_min = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    humidity_max = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    humidity = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True,
        help_text='Relative humidity (%)')
    humidity_deviation = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    humidity_outliers = models.PositiveIntegerField(
        blank=True, null=True)

    wind_direction_max = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_direction_min = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_direction = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True,
        help_text='Wind direction (° from N)')
    wind_direction_deviation = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_direction_outliers = models.PositiveIntegerField(
        blank=True, null=True)

    wind_speed_max = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True,
        help_text='Wind gust (km/h)')
    wind_speed_min = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_speed = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True,
        help_text='Wind speed (km/h)')
    wind_speed_deviation = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_speed_outliers = models.PositiveIntegerField(
        blank=True, null=True)

    wind_speed_max_kn = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_speed_min_kn = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_speed_kn = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    wind_speed_deviation_kn = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)

    rainfall = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)

    actual_rainfall = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    actual_pressure = models.DecimalField(
        max_digits=5, decimal_places=1, blank=True, null=True)

    dew_point = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)

    def gm_date(self):
        import calendar
        return calendar.timegm(self.date.timetuple())*1000

    def local_date(self):
        return timezone.localtime(self.date).isoformat().rsplit('.')[0]

    def dew_point(self):
        """
        Given the relative humidity and the dry bulb (actual) temperature,
        calculates the dew point (one-minute average).

        The constants a and b are dimensionless, c and d are in degrees
        celsius.

        Using the equation from:
             Buck, A. L. (1981), "New equations for computing vapor pressure
             and enhancement factor", J. Appl. Meteorol. 20: 1527-1532
        """
        T = float(self.temperature)
        RH = float(self.humidity)

        if not RH:
            return '0.0'

        d = 234.5

        if T > 0:
            # Use the set of constants for 0 <= T <= 50 for <= 0.05% accuracy.
            b = 17.368
            c = 238.88
        else:
            # Use the set of constants for -40 <= T <= 0 for <= 0.06% accuracy.
            b = 17.966
            c = 247.15

        gamma = math.log(RH / 100 * math.exp((b - (T / d)) * (T / (c + T))))
        return '%.2f' % ((c * gamma) / (b - gamma))
    dew_point.short_description = 'Dew point (°Celsius)'

    def get_pressure(self):
        """
        Convert the pressure from absolute pressure into sea-level adjusted
        atmospheric pressure.
        Uses the barometric formula.
        Returns the mean sea-level pressure values in hPa.
        """
        temp = float(self.temperature) + 273.15
        pressure = float(self.pressure) * 100
        g0 = 9.80665
        M = 0.0289644
        R = 8.31432
        lapse_rate = -0.0065
        height = float(getattr(self.station.location, 'height', 0))
        return '%0.2f' % (pressure / math.pow(
            temp / (temp + (lapse_rate * height)),
            (g0 * M) / (R * lapse_rate)) / 100)

    def get_rainfall(self):
        """
        Compute the rainfall difference between this reading and the previous
        reading.
        If there are no previous readings, return 0.
        If previous reading > this reading, return 0 (counter was reset).
        """
        try:
            previous = self._meta.default_manager.filter(station=self.station, date__lt=self.date).exclude(pk=self.pk).order_by('-date').first()
        except WeatherObservation.DoesNotExist:
            return Decimal('0.0')
        if previous.rainfall > self.rainfall:
            return Decimal('0.0')
        return Decimal(self.rainfall) - previous.rainfall

    def __str__(self):
        return 'Data for {} on {}'.format(self.station.name, self.date)

    class Meta:
        ordering = ['-date']
        unique_together = ('station', 'date')
