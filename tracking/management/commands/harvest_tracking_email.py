from tracking.harvest import harvest_tracking_email
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Runs harvest_tracking_email to harvest points"

    def handle(self, *args, **options):
        harvest_tracking_email()
