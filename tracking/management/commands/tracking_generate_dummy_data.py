import logging
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from tracking.models import Device, LoggedPoint

logger = logging.getLogger("organisation")


class Command(BaseCommand):
    help = "Generates dummy data (Device, LoggedPoint) for development purposes. Only runs when DEBUG=True; never use in production."

    def add_arguments(self, parser):
        parser.add_argument(
            "--devices",
            action="store",
            type=int,
            default=5,
            dest="devices",
            help="Number of dummy Device records to generate (default 5)",
        )
        parser.add_argument(
            "--logged-points",
            action="store",
            type=int,
            default=20,
            dest="logged_points",
            help="Number of dummy LoggedPoint records to generate (default 20)",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command generates dummy data and may only be run with DEBUG=True (development use only).")

        for name in ("devices", "logged_points"):
            if options[name] < 0:
                raise CommandError(f"{name} must be a non-negative integer (got {options[name]})")

        logger.info("Generating dummy data for development purposes")

        from mixer.backend.django import mixer

        with transaction.atomic():
            devices = self._generate_devices(mixer, options["devices"])
            logged_points = self._generate_logged_points(mixer, options["logged_points"], devices)

        summary = f"Created {len(devices)} devices and {len(logged_points)} logged points (dummy data for development)"
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(summary))

    def _generate_devices(self, mixer, count):
        devices = []
        districts = [choice[0] for choice in Device._meta.get_field("district").choices]
        symbols = [choice[0] for choice in Device._meta.get_field("symbol").choices if choice[0]]
        source_device_types = [choice[0] for choice in Device._meta.get_field("source_device_type").choices]
        names = ["Alex", "Brianna", "Chloe", "Daniel", "Emma", "Finn", "Grace", "Hugo", "Iris", "Jack"]
        locations = [
            "Perth Airport",
            "Wanneroo",
            "Bayswater",
            "Kwinana",
            "Mandurah",
            "Midland",
            "Jandakot",
            "Rockingham",
            "Joondalup",
            "Fremantle",
        ]
        callsigns = ["SW-01", "SW-02", "SW-07", "R-12", "OPS-3", "AER-5", "FW-09"]
        perth_centroid = {
            "lat": -31.95,
            "lon": 115.86,
        }

        for index in range(count):
            symbol = random.choice(symbols)
            registration = (
                f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
                f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
                f"{random.randint(100, 999)}"
                f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
            )
            device = mixer.blend(
                Device,
                deviceid=f"DEV-{index + 1:04d}-{random.randint(100, 999)}",
                registration=registration,
                symbol=symbol,
                district=random.choice(districts),
                source_device_type=random.choice(source_device_types),
                usual_driver=random.choice(names),
                current_driver=random.choice(names),
                usual_location=random.choice(locations),
                callsign=random.choice(callsigns),
                seen=timezone.now() - timedelta(minutes=random.randint(5, 360)),
                heading=random.randint(0, 359),
                velocity=random.randint(0, 80000),
                altitude=random.randint(0, 250),
                message=random.choice([3, 25, 26, 18]),
                point=Point(
                    perth_centroid["lon"] + random.uniform(-0.08, 0.08),
                    perth_centroid["lat"] + random.uniform(-0.06, 0.06),
                ),
                internal_only=random.choice([True, False]),
                hidden=False,
                fire_use=random.choice([True, False, None]),
            )
            if symbol in {"heavy duty", "gang truck", "dozer", "grader", "loader", "tender", "float"}:
                device.rin_number = random.randint(1, 999)
                device.save()
            devices.append(device)
        return devices

    def _generate_logged_points(self, mixer, count, devices=None):
        logged_points = []
        if count == 0:
            return logged_points

        if devices is None:
            devices = [mixer.blend(Device) for _ in range(max(1, min(count, 5)))]

        source_device_types = [choice[0] for choice in LoggedPoint._meta.get_field("source_device_type").choices]
        start_time = timezone.now() - timedelta(days=2)
        perth_centroid = {"lat": -31.95, "lon": 115.86}

        for index in range(count):
            device = random.choice(devices)
            seen = start_time + timedelta(minutes=index * 20 + random.randint(0, 19))
            point = Point(
                perth_centroid["lon"] + random.uniform(-0.04, 0.04),
                perth_centroid["lat"] + random.uniform(-0.03, 0.03),
            )
            logged_point = mixer.blend(
                LoggedPoint,
                device=device,
                seen=seen,
                point=point,
                heading=random.randint(0, 359),
                velocity=random.randint(0, 120000),
                altitude=random.randint(0, 400),
                message=random.choice([3, 25, 26, 18, 5]),
                source_device_type=device.source_device_type or random.choice(source_device_types),
                raw=f"dummy-data generated for {device.deviceid} at {seen.isoformat()}",
            )
            logged_points.append(logged_point)
        return logged_points
