from django.core.management.base import BaseCommand

from tracking.harvest import save_netstar_feed


class Command(BaseCommand):
    help = "Runs save_netstar_feed to harvest points from Netstar API"

    def handle(self, *args, **options):
        save_netstar_feed()
