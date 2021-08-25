from django.core.management.base import BaseCommand
from tracking.harvest import save_fleetcare_db


class Command(BaseCommand):
    help = "Runs save_fleetcare_db to harvest points"

    def handle(self, *args, **options):
        save_fleetcare_db()
