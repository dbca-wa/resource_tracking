from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
import logging
import math


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


def actual_rainfall(rainfall, station, timestamp=None):
    """Utility function to calculate the actual minute-rainfall for an
    observation at a station. This function is only used at the time of
    observation capture (i.e. it assumes that it is being used to calculate
    actual rainfall for a new observation). Always returns a Decimal object
    with a maximum precision of two decimal places.

    Where a rainfall counter value for a station is passed in, compute the
    rainfall over the previous minute. Subtract this counter value from the
    most recent previous counter value, determine the number of minutes
    between this observation and the previous one, then return a corrected
    rainfall total (mm).

    Where no previous observations exist or the current counter value is less
    than the previous one (implies a reset), return zero. If the passed-in
    rainfall value is 0, return zero.
    """
    from .models import WeatherObservation

    rainfall = Decimal(rainfall)
    if rainfall == 0:
        return rainfall

    # If there are no saved observations for the station, return zero.
    # Subsequent observations will return a value for actual rainfall.
    if not WeatherObservation.objects.filter(station=station).exists():
        return Decimal('0.0')

    previous_obs = WeatherObservation.objects.filter(station=station).latest('date')
    if not previous_obs.rainfall:  # If there was no previous rainfall value, return zero.
        return Decimal('0.0')
    counter_diff = rainfall - previous_obs.rainfall  # Rainfall counter.
    if counter_diff < 0:  # Less than 0 implies a counter reset (return zero)
        return Decimal('0.0')

    seconds_diff = (timestamp - previous_obs.date).total_seconds()
    # If the returned observation occurred after the timestamp, return zero.
    if seconds_diff <= 0:
        return Decimal('0.0')

    # Only bother with a correction if the time difference is >90 sec.
    if seconds_diff > 90:
        correction = 60.0 / seconds_diff
    else:
        correction = 1.0

    difference_corrected = float(counter_diff) * correction
    if difference_corrected < 0.1:  # Lowest precision for rainfall is 1 d.p.
        return Decimal('0.0')
    else:
        return Decimal('{:.1f}'.format(difference_corrected))


def download_data():
    """A utility function to check all active weather stations to see
    if a new weather observation needs to be downloaded from each.

    NOTE: this method for polling stations to download observation data is
    deprecated in favour of the standalone pollstations.py script.
    """
    from .models import WeatherStation
    observations = []
    logger = logging.getLogger('weather')

    for station in WeatherStation.objects.filter(active=True):
        logger.info("Checking station {}".format(station))

        now = timezone.now().replace(second=0, microsecond=0)
        last_scheduled = station.last_scheduled
        connect_every = timedelta(minutes=station.connect_every)
        next_scheduled = last_scheduled + connect_every
        schedule = next_scheduled.utctimetuple() <= now.utctimetuple()

        logger.info("Last scheduled: {}, connect every: {} minutes".format(
            station.last_scheduled, station.connect_every))
        logger.info("Next: {}".format(next_scheduled))
        logger.info("Now: {}, schedule new: {}".format(now, schedule))

        if schedule:
            logger.info("Scheduling {} for a new observation".format(station))
            station.last_scheduled = now
            station.save()
            result = station.download_observation()
            if result:
                logger.info("Finished collecting observation for {}".format(station.name))
                pk, response, retrieval_time = result
                observations.append(station.save_observation(response))
            else:
                logger.info("Observation failed for {}".format(station.name))
        else:
            logger.info("Skipping {}".format(station))

    return observations
