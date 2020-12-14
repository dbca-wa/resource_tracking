from django.core.management.base import BaseCommand, CommandError
from tracking.harvest import save_tracplus


class Command(BaseCommand):
    help = "Runs harvest_tracking_trackplus to harvest points"

    def handle(self, *args, **options):

        self.stdout.write("Harvesting TracPlus feed")
        try:
            out = save_tracplus()
            self.stdout.write(self.style.SUCCESS("Update {} TracPlus units; total {}".format(*out)))
        except Exception as e:
            raise CommandError(e)
