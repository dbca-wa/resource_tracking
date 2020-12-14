from django.core.management.base import BaseCommand, CommandError
from tracking.harvest import save_dfes_avl


class Command(BaseCommand):
    help = "Runs save_dfes_avl to harvest points from DFES API"

    def handle(self, *args, **options):

        self.stdout.write("Harvesting DFES tracking data feed")
        try:
            out = save_dfes_avl()
            self.stdout.write(self.style.SUCCESS("Harvested {} from DFES; created {}, updated {}, ignored {}; earliest {}, latest {}.".format(*out)))
        except Exception as e:
            raise CommandError(e)
