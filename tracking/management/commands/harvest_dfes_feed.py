from tracking.harvest import save_dfes_avl
from django.core.management.base import BaseCommand

import logging
LOGGER = logging.getLogger('tracking_points')

class Command(BaseCommand):
    help = "Runs harvest_tracking_email to harvest points"

    def handle(self, *args, **options):


        LOGGER.info('Harvesting DFES feed')
        try:
            updated, num_records = save_dfes_avl()
            print("Updated {} of {} scanned DFES devices".format(updated, num_records))
            #LOGGER.info("Updated {} of {} scanned DFES devices".format(updated, num_records))
        except Exception as e:
            LOGGER.error(e)

