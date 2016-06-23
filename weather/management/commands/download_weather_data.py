from django.core.management.base import BaseCommand
from weather.tasks import cron


class Command(BaseCommand):
    help = "Runs cron to download weather observation data"

    def handle(self, *args, **options):
        cron()
