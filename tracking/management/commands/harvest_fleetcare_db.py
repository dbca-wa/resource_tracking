from django.core.management.base import BaseCommand, CommandError
from tracking.harvest import save_fleetcare_db


class Command(BaseCommand):
    help = "Runs save_fleetcare_db to harvest points"

    def handle(self, *args, **options):

        self.stdout.write("Harvesting Fleetcare tracking data")
        try:
            out = save_fleetcare_db()
            self.stdout.write(self.style.SUCCESS("Harvested {} from Fleetcare; created {}, updated {}, ignored {}".format(*out)))
        except Exception as e:
            raise CommandError(e)
