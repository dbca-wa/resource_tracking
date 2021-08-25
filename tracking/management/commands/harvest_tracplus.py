from django.core.management.base import BaseCommand
from tracking.harvest import save_tracplus


class Command(BaseCommand):
    help = "Runs harvest_tracking_trackplus to harvest points"

    def handle(self, *args, **options):
        save_tracplus()
