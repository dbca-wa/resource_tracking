from __future__ import absolute_import
import csv
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from ftplib import FTP
import logging
import StringIO

from weather.models import WeatherStation, WeatherObservation
from weather.utils import dafwa_obs

logger = logging.getLogger('weather')


def ftp_upload(observations):
    """Utility function to upload weather data to the DAFWA FTP site in a
    suitable format.
    """
    logger.info('Connecting to {}'.format(settings.DAFWA_UPLOAD_HOST))

    try:
        ftp = FTP(settings.DAFWA_UPLOAD_HOST)
        ftp.login(settings.DAFWA_UPLOAD_USER, settings.DAFWA_UPLOAD_PASSWORD)
        ftp.cwd(settings.DAFWA_UPLOAD_DIR)
    except Exception as e:
        logger.error('Connection to {} failed'.format(settings.DAFWA_UPLOAD_HOST))
        logger.exception(e)
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
            logger.error("DAFWA upload failed for {}".format(observation))
            logger.exception(e)
            return False

    ftp.quit()
    logger.info('Published to DAFWA successfully')


def download_data():
    """A utility function to check all active weather stations to see
    if a new weather observation needs to be downloaded from each.
    """
    logger.info("Scheduling new gatherers...")
    observations = []
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
            result = station.download_observation()
            if result:
                logger.info("Finished collecting observation for {}".format(station.name))
                pk, response, retrieval_time = result
                observations.append(station.save_weather_data(response, retrieval_time))
            else:
                logger.info("Observation failed for {}".format(station.name))
        else:
            logger.info("Skipping {}".format(station))

    return observations


def upload_data(observations=None):
    """Utility function to upload observations to DAFWA.
    """
    if settings.DAFWA_UPLOAD:
        if not observations:
            # Check if there are any observations for
            # the last minute and upload them to DAFWA if so.
            now = timezone.now().replace(second=0, microsecond=0)
            last_minute = now - timedelta(minutes=1)
            observations = WeatherObservation.objects.filter(date__gte=last_minute)
        if len(observations) > 0:
            logger.info("{} observations to upload".format(len(observations)))
            ftp_upload(observations)
    return True
