from django.core.management.base import BaseCommand
from weather.models import WeatherStation


class Command(BaseCommand):
    help = 'Outputs a string containing IP:PORT:INTERVAL for all active weather stations (comma-separated).'

    def handle(self, *args, **options):
        l = ['{}:{}:{}'.format(i.ip_address, i.port, i.connect_every) for i in WeatherStation.objects.filter(active=True)]
        self.stdout.write(','.join(l))
