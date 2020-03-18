from django.core.management.base import BaseCommand, CommandError
from radio import simplify

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
            return

        if tx:
            print("Begin to simplify repeater's tx coverage polygons")
            simplify.simplify(scope=simplify.TX,enforce=enforce)
            print("End to simplify repeater's tx coverage polygons")

        if rx:
            print("Begin to simplify repeater's rx coverage polygons")
            simplify.simplify(scope=simplify.RX,enforce=enforce)
            print("End to simplify repeater's rx coverage polygons")
