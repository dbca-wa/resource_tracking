# coding=utf8
from __future__ import absolute_import, unicode_literals, division

from datetime import datetime
import pytz
import json
import logging

from django.contrib.auth.models import Group, User
from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.core.validators import MaxValueValidator

logger = logging.getLogger(__name__)


DISTRICT_PERTH_HILLS = 'PHS'
DISTRICT_SWAN_COASTAL = 'SWC'
DISTRICT_BLACKWOOD = 'BWD'
DISTRICT_WELLINGTON = 'WTN'
DISTRICT_DONNELLY = 'DON'
DISTRICT_FRANKLAND = 'FRK'
DISTRICT_ALBANY = 'ALB'
DISTRICT_ESPERANCE = 'ESP'
DISTRICT_EAST_KIMBERLEY = 'EKM'
DISTRICT_WEST_KIMBERLEY = 'WKM'
DISTRICT_EXMOUTH = 'EXM'
DISTRICT_PILBARA = 'PIL'
DISTRICT_KALGOORLIE = 'KAL'
DISTRICT_GERALDTON = 'GER'
DISTRICT_MOORA = 'MOR'
DISTRICT_SHARK_BAY = 'SHB'
DISTRICT_GREAT_SOUTHERN = 'GSN'
DISTRICT_CENTRAL_WHEATBELT = 'CWB'
DISTRICT_SOUTHERN_WHEATBELT = 'SWB'
DISTRICT_AVIATION = 'AV'
DISTRICT_OTHER = 'OTH'

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
    (DISTRICT_SOUTHERN_WHEATBELT, "Southern Wheatbelt"),
    (DISTRICT_AVIATION, "Aviation"),
    (DISTRICT_OTHER, "Other")
)

SYMBOL_CHOICES = (
    ("2 wheel drive", "2-Wheel Drive"),
    ("4 wheel drive passenger", "4-Wheel Drive Passenger"),
    ("4 wheel drive ute", "4-Wheel Drive (Ute)"),
    ("light unit", "Light Unit"),
    ("heavy duty", "Heavy Duty"),
    ("gang truck", "Gang Truck"),
    (None, ""),
    ("dozer", "Dozer"),
    ("grader", "Grader"),
    ("loader", "Loader"),
    ("tender", "Tender"),
    ("float", "Float"),
    ("snorkel", "Snorkel"),
    (None, ""),
    ("fixed wing aircraft", "Waterbomber"),
    ("rotary aircraft", "Rotary"),
    ("spotter aircraft", "Spotter"),
    ("helitac", "Helitac"),
    ("rescue helicopter", "Rescue Helicopter"),
    ("aviation fuel truck", "Aviation Fuel Truck"),
    (None, ""),
    ("comms bus", "Communications Bus"),
    ("boat", "Boat"),
    ("person", "Person"),
    ("other", "Other")
)

RAW_EQ_CHOICES = (
    (1,  "Accessories Turned ON Message"),
    (2,  "Accessories Turned OFF Message"),
    (3,  "Tracking Message"),
    (5,  "Remote Polling Message"),
    (18, "Emergency Message"),
    (19, "Remote Command Acknowledge for Emergency Turn Off"),
    (25, "Start Moving"),
    (26, "Stop Moving")
)


class BasePoint(models.Model):
    point = models.PointField(null=True, editable=False)
    heading = models.PositiveIntegerField(default=0, help_text="Heading in degrees", editable=False)
    velocity = models.PositiveIntegerField(default=0, help_text="Speed in metres/hr", editable=False)
    altitude = models.IntegerField(default=0, help_text="Altitude above sea level in metres", editable=False)
    seen = models.DateTimeField(null=True, editable=False)
    message = models.PositiveIntegerField(default=3, choices=RAW_EQ_CHOICES)

    class Meta:
        abstract = True
        ordering = ['-seen']


@python_2_unicode_compatible
class Device(BasePoint):
    deviceid = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=32, default="No Rego", verbose_name="Registration", help_text="e.g. 1QBB157")
    callsign = models.CharField(max_length=32, default="No RIN", verbose_name="Resource Identification Number (RIN)", help_text="e.g. HD123, GT456 or P789")
    rin_number = models.PositiveIntegerField(validators=[MaxValueValidator(999)], verbose_name="Resource Identification Number (RIN)", null=True, blank=True, help_text="Heavy Duty, Gang Truck or Plant only (HD/GT/P automatically prefixed). e.g. Entering 123 for a Heavy Duty will display as HD123, 456 for Gang Truck as GT456 and 789 for Plant as P789.")
    symbol = models.CharField(max_length=32, choices=SYMBOL_CHOICES, default="other")
    district = models.CharField(max_length=32, choices=DISTRICT_CHOICES, default=DISTRICT_OTHER)
    usual_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. John Jones")
    usual_callsign = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. DON99")
    usual_location = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Karijini National Park")
    current_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Jodie Jones")
    current_callsign = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. FRK99")
    is_contractor = models.BooleanField(default=False)
    contractor_details = models.CharField(max_length=50, null=True, blank=True, help_text="Person engaging contractor is responsible for maintaining contractor resource details")

    @property
    def rin_display(self):
        if not self.rin_number:
            return None
        if self.symbol == "heavy duty":
            symbol_prefix = "HD"
        elif self.symbol == "gang truck":
            symbol_prefix = "GT"
        elif self.symbol in ("grader", "dozer", "loader"):
            symbol_prefix = "P"
        else:
            return None
        display = symbol_prefix + str(self.rin_number)
        return display

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
        return naturaltime(self.seen).replace(u'\xa0', u' ')

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
            try:
                self.message = int(sbd.get("EQ", self.message))
            except:
                self.message = 3
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
            self.device.message = self.message
            self.device.save()
        return self

    class Meta:
        unique_together = (("device", "seen"),)

@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # Set is_staff to True so users can edit Device details
    instance.is_staff = True

@receiver(post_save, sender=User)
def user_post_save(sender, instance, **kwargs):
    # Add users to the 'Edit Resource Tracking Device' group so users can edit Device details
    # NOTE: does not work when saving user in Django Admin
    g = Group.objects.get(name='Edit Resource Tracking Device')
    instance.groups.add(g)
