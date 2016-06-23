from django.core.management.base import BaseCommand
from weather.tasks import download_data


class Command(BaseCommand):
    help = 'Downloads weather observation data according to schedule'

    def handle(self, *args, **options):
        download_data()
