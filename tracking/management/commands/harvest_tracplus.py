from tracking.harvest import save_tracplus
from django.core.management.base import BaseCommand

import logging
LOGGER = logging.getLogger('tracking_points')

class Command(BaseCommand):
    help = "Runs harvest_tracking_trackplus to harvest points"

    def handle(self, *args, **options):
        
        LOGGER.info('Harvesting TracPlus feed')
        try:
            save_tracplus()
        except Exception as e:
            LOGGER.error(e)


