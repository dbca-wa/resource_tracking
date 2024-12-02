from django.core.management.base import BaseCommand

from tracking.harvest import save_tracertrak_feed


class Command(BaseCommand):
    help = "Runs save_tracertrak_feed to harvest points from the TracerTrak API"

    def handle(self, *args, **options):
        save_tracertrak_feed()
