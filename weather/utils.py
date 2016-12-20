from __future__ import unicode_literals, absolute_import
import csv
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from ftplib import FTP
import logging
import math
import StringIO


LOGGER = logging.getLogger('weather')


def dafwa_obs(observation):
    """Given a passed-in WeatherObservation object, return a list of
    sensor information that is compatible with being transmitted to
    DAFWA (typically as a CSV).
    """
    reading_date = timezone.localtime(observation.date)
    return [
        observation.station.bom_abbreviation,
        reading_date.strftime('%Y-%m-%d'),
        reading_date.strftime('%H:%M:%S'),
        observation.temperature,
        observation.humidity,
        observation.wind_speed,
        observation.wind_speed_max,
        observation.wind_direction,
        observation.get_rainfall(),
        observation.station.battery_voltage,
        None,
        observation.get_pressure()
    ]


def dew_point(T, RH=None):
    """
    Given the relative humidity and the dry bulb (actual) temperature,
    calculates the dew point (one-minute average).

    The constants a and b are dimensionless, c and d are in degrees
    celsius.

    Using the equation from:
         Buck, A. L. (1981), "New equations for computing vapor pressure
         and enhancement factor", J. Appl. Meteorol. 20: 1527-1532
    """
    if RH is None:
        return "0.0"

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
    return "%.2f" % ((c * gamma) / (b - gamma))


def actual_pressure(temperature, pressure, height=0.0):
    """
    Convert the pressure from absolute pressure into sea-level adjusted
    atmospheric pressure. Returns the mean sea-level pressure values in hPa.
    Uses the barometric formula, reference
    https://en.wikipedia.org/wiki/Barometric_formula
    """
    temperature = temperature + 273.15
    pressure = pressure * 100
    g0 = 9.80665
    M = 0.0289644
    R = 8.31432
    lapse_rate = -0.0065
    return "%0.2f" % (pressure / math.pow(
        temperature / (temperature + (lapse_rate * height)),
        (g0 * M) / (R * lapse_rate)) / 100)


def actual_rainfall(rainfall, station, date):
    """
    Compute the rainfall in the last minute. We can get this by checking
    the previous weather observation's rainfall and subtracting from it
    this observation's rainfall.
    """
    from .models import WeatherObservation

    # If there are no previous readings, return 0.
    if not WeatherObservation.objects.filter(station=station).exists():
        return 0

    lastreading = WeatherObservation.objects.filter(station=station).latest('date')
    difference = rainfall - lastreading.rainfall
    diff = date - lastreading.date
    correction = 60 / diff.total_seconds()
    difference_corrected = float(difference) * correction

    return difference_corrected


def ftp_upload(observations):
    """Utility function to upload weather data to the DAFWA FTP site in a
    suitable format.
    """
    LOGGER.info('Connecting to {}'.format(settings.DAFWA_UPLOAD_HOST))

    try:
        ftp = FTP(settings.DAFWA_UPLOAD_HOST)
        ftp.login(settings.DAFWA_UPLOAD_USER, settings.DAFWA_UPLOAD_PASSWORD)
        ftp.cwd(settings.DAFWA_UPLOAD_DIR)
    except Exception as e:
        LOGGER.error('Connection to {} failed'.format(settings.DAFWA_UPLOAD_HOST))
        LOGGER.exception(e)
        return False

    output = StringIO.StringIO()
    semaphore = StringIO.StringIO()

    for observation in observations:
        # Generate the CSV for transfer.
        reading_date = timezone.localtime(observation.date)
        writer = csv.writer(output)
        writer.writerow(dafwa_obs(observation))

        output.seek(0)
        name = 'DPAW{}'.format(reading_date.strftime('%Y%m%d%H%M%S'))
        output.name = '{}.txt'.format(name)
        semaphore.name = '{}.ok'.format(name)

        try:
            # First write the data, then the semaphore file.
            ftp.storlines('STOR ' + output.name, output)
            ftp.storlines('STOR ' + semaphore.name, semaphore)
        except Exception as e:
            LOGGER.error('DAFWA upload failed for {}'.format(observation))
            LOGGER.exception(e)
            return False

    ftp.quit()
    LOGGER.info('Published to DAFWA successfully')
    return True


def download_data():
    """A utility function to check all active weather stations to see
    if a new weather observation needs to be downloaded from each.

    NOTE: this method for polling stations to download observation data is
    deprecated in favour of the standalone pollstations.py script.
    """
    from .models import WeatherStation
    LOGGER.info("Scheduling new gatherers...")
    observations = []

    for station in WeatherStation.objects.filter(active=True):
        LOGGER.info("Checking station {}".format(station))

        now = timezone.now().replace(second=0, microsecond=0)
        last_scheduled = station.last_scheduled
        connect_every = timedelta(minutes=station.connect_every)
        next_scheduled = last_scheduled + connect_every

        # Not sure why I can't directly compare them, it *sometimes* works,
        # but not every check succeeds. I wonder what the difference is...
        # Their tuples seem to be equal, so we'll use that.
        schedule = next_scheduled.utctimetuple() <= now.utctimetuple()

        LOGGER.info("Last scheduled: {}, connect every: {} minutes".format(
            station.last_scheduled, station.connect_every))
        LOGGER.info("Next: {}".format(next_scheduled))
        LOGGER.info("Now: {}, schedule new: {}".format(now, schedule))

        if schedule:
            LOGGER.info("Scheduling {} for a new observation".format(station))
            station.last_scheduled = now
            station.save()
            result = station.download_observation()
            if result:
                LOGGER.info("Finished collecting observation for {}".format(station.name))
                pk, response, retrieval_time = result
                observations.append(station.save_weather_data(response, retrieval_time))
            else:
                LOGGER.info("Observation failed for {}".format(station.name))
        else:
            LOGGER.info("Skipping {}".format(station))

    return observations


def upload_data(observations=None):
    """Utility function to upload observations to DAFWA.
    """
    from .models import WeatherObservation

    if settings.DAFWA_UPLOAD:
        if not observations:
            # Check if there are any observations for
            # the last minute and upload them to DAFWA if so.
            now = timezone.now().replace(second=0, microsecond=0)
            last_minute = now - timedelta(minutes=1)
            observations = WeatherObservation.objects.filter(date__gte=last_minute)
        if len(observations) > 0:
            LOGGER.info("{} observations to upload".format(len(observations)))
            ftp_upload(observations)
    return True
