from django.core.management.base import BaseCommand, CommandError
from weather.utils import download_data


class Command(BaseCommand):
    help = 'Downloads weather observation data according to schedule'

    def handle(self, *args, **options):
        try:
            observations = download_data()
            self.stdout.write(self.style.SUCCESS('Downloaded {} weather observations'.format(len(observations))))
        except:
            raise CommandError('Unable to download weather observations')
