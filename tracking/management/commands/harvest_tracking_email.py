from django.core.management.base import BaseCommand

from tracking.harvest import harvest_tracking_email


class Command(BaseCommand):
    help = "Runs harvest_tracking_email to harvest points from emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge-email",
            action="store_true",
            dest="purge_email",
            required=False,
            help="Mark processed email as read and flag for deletion",
        )

    def handle(self, *args, **options):
        if options.get("purge_email"):
            harvest_tracking_email(purge_email=True)
        else:
            harvest_tracking_email()
