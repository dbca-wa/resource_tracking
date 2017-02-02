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
from django.forms import ValidationError

logger = logging.getLogger(__name__)


DISTRICT_PERTH_HILLS = 'PHD'
DISTRICT_SWAN_COASTAL = 'SCD'
DISTRICT_SWAN_REGION = 'SWAN'
DISTRICT_BLACKWOOD = 'BWD'
DISTRICT_WELLINGTON = 'WTN'
DISTRICT_SOUTH_WEST_REGION = 'SWR'
DISTRICT_DONNELLY = 'DON'
DISTRICT_FRANKLAND = 'FRK'
DISTRICT_WARREN_REGION = 'WR'
DISTRICT_ALBANY = 'ALB'
DISTRICT_ESPERANCE = 'ESP'
DISTRICT_SOUTH_COAST_REGION = 'SCR'
DISTRICT_EAST_KIMBERLEY = 'EKD'
DISTRICT_WEST_KIMBERLEY = 'WKD'
DISTRICT_KIMBERLEY_REGION = 'KIMB'
DISTRICT_EXMOUTH = 'EXM'
DISTRICT_PILBARA_REGION = 'PIL'
DISTRICT_GOLDFIELDS_REGION = 'GLD'
DISTRICT_GERALDTON = 'GER'
DISTRICT_MOORA = 'MOR'
DISTRICT_SHARK_BAY = 'SHB'
DISTRICT_MIDWEST_REGION = 'MWR'
DISTRICT_CENTRAL_WHEATBELT = 'CWB'
DISTRICT_SOUTHERN_WHEATBELT = 'SWB'
DISTRICT_WHEATBELT_REGION = 'WBR'
DISTRICT_AVIATION = 'AV'
DISTRICT_OTHER = 'OTH'

DISTRICT_CHOICES = (
    (DISTRICT_SWAN_REGION, "Swan Region"),
    (DISTRICT_PERTH_HILLS, "Perth Hills"),
    (DISTRICT_SWAN_COASTAL, "Swan Coastal"),
    (DISTRICT_SOUTH_WEST_REGION, "South West Region"),
    (DISTRICT_BLACKWOOD, "Blackwood"),
    (DISTRICT_WELLINGTON, "Wellington"),
    (DISTRICT_WARREN_REGION, "Warren Region"),
    (DISTRICT_DONNELLY, "Donnelly"),
    (DISTRICT_FRANKLAND, "Frankland"),
    (DISTRICT_SOUTH_COAST_REGION, "South Coast Region"),
    (DISTRICT_ALBANY, "Albany"),
    (DISTRICT_ESPERANCE, "Esperance"),
    (DISTRICT_KIMBERLEY_REGION, "Kimberley Region"),
    (DISTRICT_EAST_KIMBERLEY, "East Kimberley"),
    (DISTRICT_WEST_KIMBERLEY, "West Kimberley"),
    (DISTRICT_EXMOUTH, "Exmouth"),
    (DISTRICT_PILBARA_REGION, "Pilbara Region"),
    (DISTRICT_GOLDFIELDS_REGION, "Goldfields Region"),
    (DISTRICT_MIDWEST_REGION, "Midwest Region"),
    (DISTRICT_GERALDTON, "Geraldton"),
    (DISTRICT_MOORA, "Moora"),
    (DISTRICT_SHARK_BAY, "Shark Bay"),
    (DISTRICT_WHEATBELT_REGION, "Wheatbelt Region"),
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
    ("snorkel", "Snorkel"),
    (None, ""),
    ("dozer", "Dozer"),
    ("grader", "Grader"),
    ("loader", "Loader"),
    ("tender", "Tender"),
    ("float", "Float"),
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

SOURCE_DEVICE_TYPE_CHOICES = (
    ("tracplus", "TracPlus"),
    ("iriditrak", "Iriditrak"),
    ("dplus", "DPlus"),
    ("spot", "Spot"),
    ("other", "Other")
)

class BasePoint(models.Model):
    point = models.PointField(null=True, editable=False)
    heading = models.PositiveIntegerField(default=0, help_text="Heading in degrees", editable=False)
    velocity = models.PositiveIntegerField(default=0, help_text="Speed in metres/hr", editable=False)
    altitude = models.IntegerField(default=0, help_text="Altitude above sea level in metres", editable=False)
    seen = models.DateTimeField(null=True, editable=False)
    message = models.PositiveIntegerField(default=3, choices=RAW_EQ_CHOICES)
    source_device_type = models.CharField(max_length=32, choices=SOURCE_DEVICE_TYPE_CHOICES, default="other")

    class Meta:
        abstract = True
        ordering = ['-seen']

    def clean_fields(self, exclude=None):
        """
        Override clean_fields to provide model-level validation.
        """
        if exclude is None:
            exclude = []
        
        errors = {}
        for f in self._meta.fields:
            if f.name in exclude:
                continue

            if hasattr(self, "clean_%s" % f.attname):
                try:
                    getattr(self, "clean_%s" % f.attname)()
                except ValidationError as e:
                    errors[f.name] = e.error_list

        try:
            super(BasePoint, self).clean_fields(exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)


@python_2_unicode_compatible
class Device(BasePoint):
    deviceid = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=7, default="No Rego", verbose_name="Registration", help_text="e.g. 1QBB157")
    rin_number = models.PositiveIntegerField(validators=[MaxValueValidator(999)], verbose_name="Resource Identification Number (RIN)", null=True, blank=True, help_text="Heavy Duty, Gang Truck or Plant only (HD/GT/P automatically prefixed). e.g. Entering 123 for a Heavy Duty will display as HD123, 456 for Gang Truck as GT456 and 789 for Plant as P789.")
    rin_display = models.CharField(max_length=5, null=True, blank=True, verbose_name="RIN")
    symbol = models.CharField(max_length=32, choices=SYMBOL_CHOICES, default="other")
    district = models.CharField(max_length=32, choices=DISTRICT_CHOICES, default=DISTRICT_OTHER, verbose_name="Region/District")
    usual_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. John Jones")
    usual_callsign = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. DON99")
    usual_location = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Karijini National Park")
    current_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Jodie Jones")
    current_callsign = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. FRK99")
    contractor_details = models.CharField(max_length=50, null=True, blank=True, help_text="Person engaging contractor is responsible for maintaining contractor resource details")
    other_details = models.TextField(null=True, blank=True)

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

    def clean_rin_number(self):
        if self.symbol in ("heavy duty", "gang truck", "dozer", "grader", "loader", "tender", "float") and not self.rin_number:
            raise ValidationError("Please enter a RIN number.")
        if self.rin_number and self.symbol not in ("heavy duty", "gang truck", "dozer", "grader", "loader", "tender", "float"):
            raise ValidationError("Please remove the RIN number or select a symbol from Heavy Duty, Gang Truck, Dozer, Grader, Loader, Tender or Float")
        if self.rin_number:
            if self.symbol == "heavy duty":
                symbol_prefix = "HD"
            elif self.symbol == "gang truck":
                symbol_prefix = "GT"
            elif self.symbol in ("grader", "dozer", "loader", "tender", "float"):
                symbol_prefix = "P"
            else:
                symbol_prefix = ""
            self.rin_display = symbol_prefix + str(self.rin_number)
        else:
            self.rin_display = None

    def __str__(self):
        return force_text("{} {}".format(self.name, self.deviceid))


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
            self.source_device_type = str(sbd.get("TY", self.source_device_type))
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
            self.device.source_device_type = self.source_device_type
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
