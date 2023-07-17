from django.core.management.base import BaseCommand
import logging
from tracking.harvest import import_fleetcare_blobs_to_staging


# Set the logging level for all azure-* libraries (the azure-storage-blob library uses this one).
# Reference: https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-logging
azure_logger = logging.getLogger("azure")
azure_logger.setLevel(logging.ERROR)


class Command(BaseCommand):
    help = "Runs import_fleetcare_blobs_to_staging to import Fleetcare raw data to staging table"

    def add_arguments(self, parser):
        parser.add_argument(
            '--staging-table', action='store', dest='staging_table', required=False, default=None,
            help='Staging table name')

    def handle(self, *args, **options):
        if options['staging_table']:
            staging_table = options['staging_table']
            import_fleetcare_blobs_to_staging(staging_table=staging_table)
        else:
            import_fleetcare_blobs_to_staging()
