from django.core.management.base import BaseCommand
from tracking.harvest import save_dfes_feed


class Command(BaseCommand):
    help = "Runs save_dfes_feed to harvest points from DFES API"

    def handle(self, *args, **options):
        save_dfes_feed()
