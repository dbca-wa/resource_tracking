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
    atmospheric pressure.
    Uses the barometric formula.
    Returns the mean sea-level pressure values in hPa.
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
    from weather.models import WeatherObservation

    # If there are no previous readings, return 0.
    if not WeatherObservation.objects.filter(station=station).exists():
        return 0

    lastreading = WeatherObservation.objects.filter(station=station).latest('date')
    difference = rainfall - lastreading.rainfall
    diff = date - lastreading.date
    correction = 60 / diff.total_seconds()
    difference_corrected = float(difference) * correction

    return difference_corrected
