from django.core.management.base import BaseCommand
from tracking.harvest import harvest_tracking_email


class Command(BaseCommand):
    help = "Runs harvest_tracking_email to harvest points from emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--device-type", action="store", dest="device_type", required=True, default=None,
            help="Tracking device type, one of: iriditrak, dplus, spot, mp70")

    def handle(self, *args, **options):
        # Specify the device type to harvest from the mailbox.
        device_type = None
        if options["device_type"] and options["device_type"] in ("iriditrak", "dplus", "spot", "mp70"):
            device_type = options["device_type"]

        harvest_tracking_email(device_type)
