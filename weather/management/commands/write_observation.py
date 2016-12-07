from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from weather.models import WeatherStation
from weather.tasks import ftp_upload


class Command(BaseCommand):
    help = 'Accepts a string argument ("IP::RAW_DATA") and writes a weather observation to the database (and optionally upload it to DAFWA).'

    def add_arguments(self, parser):
        # Required positional argument.
        parser.add_argument('string', type=str)

    def handle(self, *args, **options):
        try:
            (ip, data) = options['string'].split('::')
            station = WeatherStation.objects.get(ip_address=ip)
            obs = station.save_weather_data(data)
            self.stdout.write(self.style.SUCCESS('Recorded observation {}'.format(obs)))
        except:
            raise CommandError('Unable to parse observation string')
        if settings.DAFWA_UPLOAD:
            try:
                uploaded = ftp_upload([obs])
                if uploaded:
                    self.stdout.write(self.style.SUCCESS('Published observation to DAFWA'))
                else:
                    self.stdout.write(self.style.WARNING('Observation not published to DAFWA'))
            except:
                raise CommandError('Publish to DAFWA failed')
