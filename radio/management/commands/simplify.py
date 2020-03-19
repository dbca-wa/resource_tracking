import logging
import json

from django.core.management.base import BaseCommand, CommandError
from radio import simplify

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Simplify repeater coverage polygons'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enforce',
            action='store_true',
            help='Resimplify all repeater coverage polygons',
        )
        parser.add_argument(
            '--tx',
            action='store_true',
            help='Simplify repeater tx coverage polygons',
        )
        parser.add_argument(
            '--rx',
            action='store_true',
            help='Simplify repeater rx coverage polygons',
        )
        parser.add_argument(
            '--resolve_repeater_overlap',
            action='store_true',
            help='Resolve repeater coverage overlap',
        )


    def handle(self, *args, **options):
        logger.debug("Options = {}".format(json.dumps(options,indent=4)))
        enforce = options['enforce']
        tx = options["tx"]
        rx = options["rx"]
        resolve_repeater_overlap = options["resolve_repeater_overlap"]
        if not tx and not rx:
            logger.error("Please specify --tx or --rx to run")
            return

        if tx:
            logger.info("Begin to simplify repeater's tx coverage polygons")
            simplify.simplify(scope=simplify.TX,enforce=enforce,resolve_repeater_overlap=resolve_repeater_overlap)
            logger.info("End to simplify repeater's tx coverage polygons")

        if rx:
            logger.info("Begin to simplify repeater's rx coverage polygons")
            simplify.simplify(scope=simplify.RX,enforce=enforce,resolve_repeater_overlap=resolve_repeater_overlap)
            logger.info("End to simplify repeater's rx coverage polygons")
