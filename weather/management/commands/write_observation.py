import csv
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
import logging
import os
from weather.models import WeatherStation


class Command(BaseCommand):
    help = 'Accepts a string argument ("IP::RAW_DATA") and writes a weather observation to the database and (optionally) to the upload cache directory'

    def add_arguments(self, parser):
        # Required positional argument.
        parser.add_argument('string', type=str)

    def handle(self, *args, **options):
        try:
            (ip, data) = options['string'].split('::')
            station = WeatherStation.objects.get(ip_address=ip)
            obs = station.save_observation(data)
            self.stdout.write(self.style.SUCCESS('Recorded observation {}'.format(obs)))
        except:
            raise CommandError('Error while parsing observation string: {}'.format(data))

        if settings.DAFWA_UPLOAD:  # Write observation to the upload cache dir.
            try:
                # Ensure that the upload_data_cache directory exists.
                if not os.path.exists(os.path.join(settings.BASE_DIR, 'upload_data_cache')):
                    os.mkdir(os.path.join(settings.BASE_DIR, 'upload_data_cache'))
                # Write the observation and semaphore files.
                ts = timezone.localtime(obs.date)
                name = 'DPAW{}'.format(ts.strftime('%Y%m%d%H%M%S'))
                observation = '{}.txt'.format(name)
                semaphore = '{}.ok'.format(name)
                # Write the observation to file.
                outfile = open(os.path.join(settings.BASE_DIR, 'upload_data_cache', observation), 'w')
                writer = csv.writer(outfile)
                writer.writerow(obs.get_dafwa_obs())
                outfile.close()
                # Write the semaphore file.
                outfile = open(os.path.join(settings.BASE_DIR, 'upload_data_cache', semaphore), 'w')
                outfile.close()
                # Write the archive log.
                archivelog = open(os.path.join(settings.BASE_DIR, 'upload_data_cache', observation), 'r')
                logger = logging.getLogger('dafwa')
                logger.info(archivelog.read().strip())
                archivelog.close()
            except:
                raise CommandError('Error while writing observation to upload_data_cache')
