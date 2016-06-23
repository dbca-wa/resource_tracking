from __future__ import absolute_import
import csv
from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import force_text
from django.template.defaultfilters import date
import logging
import os
import paramiko
import StringIO
import sys
import telnetlib

from weather.models import WeatherStation, WeatherObservation

logger = logging.getLogger('weather')


def ftp_upload(host, port, username, password, observations):
    logger.debug("Connecting to {}...".format(host))

    try:
        transport = paramiko.Transport((host, port))

        transport.connect(username=username, password=password)
        client = paramiko.SFTPClient.from_transport(transport)
    except Exception as e:
        logger.error("Connection to {} failed... {} exiting".format(host, e))
        return

    output = StringIO.StringIO()

    for observation in observations:
        reading_date = timezone.localtime(observation.date)
        logger.info("Date: {}".format(reading_date))
        writer = csv.writer(output)
        writer.writerow([
            observation.station.bom_abbreviation, reading_date.date(),
            reading_date.time(), observation.temperature,
            observation.humidity, observation.wind_speed,
            observation.wind_speed_max, observation.wind_direction,
            observation.get_rainfall(),
            observation.station.battery_voltage, None,
            observation.get_pressure()
        ])

        # Reset the position to the beginning of our file-like object.
        name = "DPAW-{}".format(observation.station.bom_abbreviation)
        reading_date = date(reading_date, "YmdHis")
        output.seek(0)
        output.name = "{}{}.txt".format(name, reading_date)
        semaphore = "{}{}.ok".format(name, reading_date)
        path = settings.DAFWA_UPLOAD_DIR

        try:
            # First write the data, then the semaphore file.
            f = client.open(os.path.join(path, output.name), 'w')
            f.write(output.read())
            f.close()

            f = client.open(os.path.join(path, semaphore), 'w')
            f.write('')
            f.close()
        except:
            # The SFTP client failed, restart the connection up to three
            # times before giving up and exiting.
            logger.error("DAFWA upload failed for {}".format(observation), exc_info=sys.exc_info())

    client.close()
    logger.info("Published to DAFWA successfully.")


def retrieve_observation(args):
    station_name, ip_address, port, pk, retrieval_time = args
    logger.info("Trying to connect to {}".format(station_name))
    client, output = None, False
    try:
        client = telnetlib.Telnet(ip_address, port)
        response = client.read_until('\r\n'.encode('utf8'), 60)
        response = response[2:]
    except:
        logger.info("Failed to read weather data from {}...".format(station_name), exc_info=sys.exc_info())
    else:
        try:
            logger.info("PERIODIC READING OF {}".format(station_name))
            logger.info(force_text(response))
            output = (pk, force_text(response), retrieval_time)
            if client:
                client.close()
        except Exception, e:
            logger.info("Had some trouble saving this stuff... {}".format(e))

    logger.info("Finished collecting observation for {}".format(station_name))
    return output


def cron(request=None):
    start = timezone.now()
    """
    Check all of our active weather stations to see if we need to update their
    observations. Launch a sub-task if so that telnets to the station and
    retrieves the latest data.
    """
    logger.info("Scheduling new gatherers...")
    for station in WeatherStation.objects.filter(active=True):
        logger.info("Checking station {}".format(station))

        now = timezone.now().replace(second=0, microsecond=0)
        last_scheduled = station.last_scheduled
        connect_every = timedelta(minutes=station.connect_every)
        next_scheduled = last_scheduled + connect_every

        # Not sure why I can't directly compare them, it *sometimes* works,
        # but not every check succeeds. I wonder what the difference is...
        # Their tuples seem to be equal, so we'll use that.
        schedule = next_scheduled.utctimetuple() <= now.utctimetuple()

        logger.info("Last scheduled: {}, connect every: {} minutes".format(
            station.last_scheduled, station.connect_every))
        logger.info("Next: {}".format(next_scheduled))
        logger.info("Now: {}, schedule new: {}".format(now, schedule))

        if schedule:
            logger.info("Scheduling {} for a new observation".format(station))
            station.last_scheduled = now
            station.save()
            result = retrieve_observation((station.name, station.ip_address, station.port, station.pk, now))
            if result:
                pk, response, retrieval_time = result
                station = WeatherStation.objects.get(pk=pk)
                station.save_weather_data(response, retrieval_time)
            break
        else:
            logger.info("Skipping {}".format(station))

    if settings.DAFWA_UPLOAD:
        # Check if there are any observations for
        # the last minute and upload them to DAFWA if so.
        now = timezone.now().replace(second=0, microsecond=0)
        last_minute = now - timedelta(minutes=1)
        observations = WeatherObservation.objects.filter(date__gte=last_minute)
        if observations.count() > 0:
            logger.info("Found {} observations to publish...".format(observations.count()))
            ftp_upload(
                settings.DAFWA_UPLOAD_HOST,
                int(settings.DAFWA_UPLOAD_PORT),
                settings.DAFWA_UPLOAD_USER,
                settings.DAFWA_UPLOAD_PASSWORD,
                observations
            )

    delta = timezone.now() - start
    html = "<html><body>Cron run at {} for {}.</body></html>".format(start, delta)
    return HttpResponse(html)
