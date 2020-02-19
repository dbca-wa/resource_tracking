from tracking.harvest import save_fleetcare_db
from django.core.management.base import BaseCommand

import logging
LOGGER = logging.getLogger('tracking_points')


class Command(BaseCommand):
    help = "Runs save_fleetcare_db to harvest points"

    def handle(self, *args, **options):

        LOGGER.info('Harvesting Fleetcare tracking data')
        try:
            out = save_fleetcare_db()
            LOGGER.info("Harvested {} from Fleetcare; created {}, updated {}, ignored {}".format(*out))
        except Exception as e:
            LOGGER.error(e)
