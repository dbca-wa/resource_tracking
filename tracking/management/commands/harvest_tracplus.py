from django.core.management.base import BaseCommand
from tracking.harvest import save_tracplus_feed


class Command(BaseCommand):
    help = "Runs save_tracplus_feed to harvest points from TracPlus API"

    def handle(self, *args, **options):
        save_tracplus_feed()
