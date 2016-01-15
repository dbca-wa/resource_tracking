from resource_tracking.harvest import cron
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Runs cron to harvest points"

    def handle(self, *args, **options):
        cron()
