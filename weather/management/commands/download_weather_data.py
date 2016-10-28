from django.core.management.base import BaseCommand
from weather.tasks import download_data, upload_data


class Command(BaseCommand):
    help = 'Downloads weather observation data according to schedule'

    def handle(self, *args, **options):
        observations = download_data()
        upload_data(observations)
