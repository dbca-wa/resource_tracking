import logging

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

    def handle(self, *args, **options):
        enforce = options['enforce']
        tx = options["tx"]
        rx = options["rx"]
        if not tx and not rx:
            logger.error("Please specify --tx or --rx to run")
            return

        if tx:
            logger.info("Begin to simplify repeater's tx coverage polygons")
            simplify.simplify(scope=simplify.TX,enforce=enforce)
            logger.info("End to simplify repeater's tx coverage polygons")

        if rx:
            logger.info("Begin to simplify repeater's rx coverage polygons")
            simplify.simplify(scope=simplify.RX,enforce=enforce)
            logger.info("End to simplify repeater's rx coverage polygons")
