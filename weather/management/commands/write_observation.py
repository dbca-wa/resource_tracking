from django.core.management.base import BaseCommand, CommandError
from weather.models import WeatherStation


class Command(BaseCommand):
    help = 'Accepts a string argument ("IP::RAW_DATA") and writes a weather observation to the database.'

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
