# coding=utf8
from __future__ import absolute_import, unicode_literals, division

from datetime import datetime
import pytz
import json
import logging

from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.contrib.humanize.templatetags.humanize import naturaltime

logger = logging.getLogger(__name__)


DISTRICT_PERTH_HILLS = 1
DISTRICT_SWAN_COASTAL = 2
DISTRICT_BLACKWOOD = 3
DISTRICT_WELLINGTON = 4
DISTRICT_DONNELLY = 5
DISTRICT_FRANKLAND = 6
DISTRICT_ALBANY = 7
DISTRICT_ESPERANCE = 8
DISTRICT_EAST_KIMBERLEY = 9
DISTRICT_WEST_KIMBERLEY = 10
DISTRICT_EXMOUTH = 11
DISTRICT_PILBARA = 12
DISTRICT_KALGOORLIE = 13
DISTRICT_GERALDTON = 14
DISTRICT_MOORA = 15
DISTRICT_SHARK_BAY = 16
DISTRICT_GREAT_SOUTHERN = 17
DISTRICT_CENTRAL_WHEATBELT = 18
DISTRICT_SOUTHERN_WHEATBELT = 19

DISTRICT_CHOICES = (
    (DISTRICT_PERTH_HILLS, "Perth Hills"),
    (DISTRICT_SWAN_COASTAL, "Swan Coastal"),
    (DISTRICT_BLACKWOOD, "Blackwood"),
    (DISTRICT_WELLINGTON, "Wellington"),
    (DISTRICT_DONNELLY, "Donnelly"),
    (DISTRICT_FRANKLAND, "Frankland"),
    (DISTRICT_ALBANY, "Albany"),
    (DISTRICT_ESPERANCE, "Esperance"),
    (DISTRICT_EAST_KIMBERLEY, "East Kimberley"),
    (DISTRICT_WEST_KIMBERLEY, "West Kimberley"),
    (DISTRICT_EXMOUTH, "Exmouth"),
    (DISTRICT_PILBARA, "Pilbara"),
    (DISTRICT_KALGOORLIE, "Kalgoorlie"),
    (DISTRICT_GERALDTON, "Geraldton"),
    (DISTRICT_MOORA, "Moora"),
    (DISTRICT_SHARK_BAY, "Shark Bay"),
    (DISTRICT_GREAT_SOUTHERN, "Great Southern"),
    (DISTRICT_CENTRAL_WHEATBELT, "Central Wheatbelt"),
    (DISTRICT_SOUTHERN_WHEATBELT, "Southern Wheatbelt")
)

SYMBOL_CHOICES = (
    ("4 wheel drive passenger", "4-Wheel Drive Passenger"),
    ("4 wheel drive ute", "4-Wheel Drive (Ute)"),
    ("boat", "Boat"),
    ("comms bus", "Communications Bus"),
    ("dozer", "Dozer"),
    ("fixed wing aircraft", "Fixed-wing Aircraft"),
    ("float", "Float"),
    ("gang truck", "Gang Truck"),
    ("grader", "Grader"),
    ("heavy duty", "Heavy Duty"),
    ("light unit", "Light Unit"),
    ("loader", "Loader"),
    ("other", "Other"),
    ("person", "Person"),
    ("rotary aircraft", "Rotary Aircraft"),
    ("snorkel", "Snorkel"),
    ("tender", "Tender")
)

class BasePoint(models.Model):
    point = models.PointField(null=True, editable=False)
    heading = models.PositiveIntegerField(default=0, help_text="Heading in degrees", editable=False)
    velocity = models.PositiveIntegerField(default=0, help_text="Speed in metres/hr", editable=False)
    altitude = models.IntegerField(default=0, help_text="Altitude above sea level in metres", editable=False)
    seen = models.DateTimeField(null=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['-seen']


@python_2_unicode_compatible
class Device(BasePoint):
    deviceid = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=32, default="No Name", verbose_name="Rego", help_text="e.g. 1QBB157")
    callsign = models.CharField(max_length=32, default="No Callsign", verbose_name="Vehicle ID", help_text="e.g. GT124, HD121")
    symbol = models.CharField(max_length=32, choices=SYMBOL_CHOICES, default="Other")
    district = models.CharField(max_length=32, choices=DISTRICT_CHOICES, null=True, blank=True)

    @property
    def age_minutes(self):
        if not self.seen:
            return None
        delta = timezone.now() - self.seen
        minutes = delta.days * 24 * 60 + delta.seconds // 60
        return minutes

    @property
    def age_colour(self):
        # returns age in colour
        minutes = self.age_minutes
        if minutes is None:
            colour = 'red'
        elif minutes < 60:
            colour = 'green'
        elif minutes < 180:
            colour = 'orange'
        else:
            colour = 'red'
        return colour

    @property
    def age_text(self):
        # returns age in humanized form
        return naturaltime(self.seen)

    @property
    def icon(self):
        return "sss-{}".format(self.symbol.lower().replace(" ", "_"))

    def __str__(self):
        if self.callsign == "No Callsign":
            callsign = self.name
        callsign = self.callsign
        return force_text("{} {}".format(callsign, self.deviceid))


@python_2_unicode_compatible
class LoggedPoint(BasePoint):
    device = models.ForeignKey(Device, editable=False)
    raw = models.TextField(editable=False)

    def __str__(self):
        return force_text("{} {}".format(self.device, self.seen))

    @classmethod
    def parse_sbd(cls, sbd):
        """
        parses an sbd into a persisted LoggedPoint object
        handles duplicates
        """
        device = Device.objects.get_or_create(deviceid=sbd["ID"])[0]
        if sbd.get("LG", 0) == 0 or sbd.get("LT", 0) == 0:
            logger.warn("Bad geometry for {}, discarding".format(device))
            return None
        seen = timezone.make_aware(datetime.fromtimestamp(float(sbd['TU'])), pytz.timezone("UTC"))
        self, created = cls.objects.get_or_create(device=device, seen=seen)
        if created:
            self.point = 'POINT({LG} {LT})'.format(**sbd)
            self.heading = abs(sbd.get("DR", self.heading))
            self.velocity = abs(sbd.get("VL", self.heading))
            self.altitude = int(sbd.get("AL", self.altitude))
            self.raw = json.dumps(sbd)
            self.save()
            logger.info("LoggedPoint {} created.".format(self))
        else:
            logger.info("LoggedPoint {} found to be a duplicate.".format(self))
        if self.device.seen is None or self.seen > self.device.seen:
            self.device.seen = self.seen
            self.device.point = self.point
            self.device.heading = self.heading
            self.device.velocity = self.velocity
            self.device.altiitude = self.altitude
            self.device.save()
        return self

    class Meta:
        unique_together = (("device", "seen"),)
