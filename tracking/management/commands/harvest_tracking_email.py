from django.core.management.base import BaseCommand, CommandError
from tracking.harvest import harvest_tracking_email


class Command(BaseCommand):
    help = "Runs harvest_tracking_email to harvest points from emails"

    def handle(self, *args, **options):
        self.stdout.write("Harvesting email tracking data")
        try:
            harvest_tracking_email()
            self.stdout.write(self.style.SUCCESS("Complete"))
        except Exception as e:
            raise CommandError(e)
