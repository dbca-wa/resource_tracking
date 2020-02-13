from tracking.harvest import save_fleetcare_db
from django.core.management.base import BaseCommand

import logging
LOGGER = logging.getLogger('tracking_points')

class Command(BaseCommand):
    help = "Runs save_fleetcare_db to harvest points"

    def handle(self, *args, **options):


        LOGGER.info('Harvesting fleetcare database')
        try:
            print("Harvested {} from Fleetcare; created {}, updated {}, ingored {}; Earliest seen {}, Lastest seen {}.".format(*save_dfes_avl()))
            #LOGGER.info("Updated {} of {} scanned DFES devices".format(updated, num_records))
        except Exception as e:
            LOGGER.error(e)

