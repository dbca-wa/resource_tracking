# coding=utf8
from datetime import datetime
import pytz
import json
import logging

from django.contrib.auth.models import Group, User
from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.encoding import force_text
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.core.validators import MaxValueValidator
from django.forms import ValidationError

LOGGER = logging.getLogger('tracking')


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
DISTRICT_PILBARA_REGION = 'PIL'
DISTRICT_EXMOUTH = 'EXM'
DISTRICT_GOLDFIELDS_REGION = 'GLD'
DISTRICT_GERALDTON = 'GER'
DISTRICT_KALBARRI = 'KLB'
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
    (DISTRICT_PILBARA_REGION, "Pilbara Region"),
    (DISTRICT_EXMOUTH, "Exmouth"),
    (DISTRICT_GOLDFIELDS_REGION, "Goldfields Region"),
    (DISTRICT_MIDWEST_REGION, "Midwest Region"),
    (DISTRICT_GERALDTON, "Geraldton"),
    (DISTRICT_KALBARRI, "Kalbarri"),
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
    ("dozer", "Dozer"),
    ("grader", "Grader"),
    ("loader", "Loader"),
    ("tender", "Tender"),
    ("float", "Float"),
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
    ("other", "Other"),
    ("unknown", "Unknown")
)

RAW_EQ_CHOICES = (
    (1, "Accessories Turned ON Message"),
    (2, "Accessories Turned OFF Message"),
    (3, "Tracking Message"),
    (5, "Remote Polling Message"),
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
    ("dfes", "DFES"),
    ("mp70", "MP70"),
    ("fleetcare", "fleetcare"),
    ("other", "Other"),
    ("fleetcare_error", "Fleetcare (error)")
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


class Device(BasePoint):
    deviceid = models.CharField(max_length=32, unique=True)
    registration = models.CharField(max_length=32, default="No Rego", help_text="e.g. 1QBB157")
    rin_number = models.PositiveIntegerField(validators=[MaxValueValidator(999)], verbose_name="Resource Identification Number (RIN)", null=True, blank=True, help_text="Heavy Duty, Gang Truck or Plant only (HD/GT/P automatically prefixed).")
    rin_display = models.CharField(max_length=5, null=True, blank=True, verbose_name="RIN")
    symbol = models.CharField(max_length=32, choices=SYMBOL_CHOICES, default="other")
    district = models.CharField(max_length=32, choices=DISTRICT_CHOICES, default=DISTRICT_OTHER, verbose_name="Region/District")
    district_display = models.CharField(max_length=100, default='Other', verbose_name="District")
    usual_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. John Jones")
    usual_location = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Karijini National Park")
    current_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Jodie Jones")
    callsign = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. 99 for Heavy Duty, Gang Truck or Plant, or free text for other devices")
    callsign_display = models.CharField(max_length=50, null=True, blank=True, verbose_name="Callsign")
    contractor_details = models.CharField(max_length=50, null=True, blank=True, help_text="Person engaging contractor is responsible for maintaining contractor resource details")
    other_details = models.TextField(null=True, blank=True)
    internal_only = models.BooleanField(default=False, verbose_name="Internal to DBCA only")
    hidden = models.BooleanField(default=False, verbose_name="Hidden/private use")
    deleted = models.BooleanField(default=False, verbose_name="Deleted?")

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

    def clean_district(self):
        if self.district:
            self.district_display = self.get_district_display()

    def clean_callsign(self):
        if self.symbol in ("heavy duty", "gang truck", "dozer", "grader", "loader", "tender", "float") and not self.callsign:
            raise ValidationError("Please enter a Callsign number.")
        if self.callsign and self.symbol in ("heavy duty", "gang truck", "dozer", "grader", "loader", "tender", "float"):
            try:
                self.callsign = abs(int(str(self.callsign)))
            except:
                raise ValidationError("Callsign must be a number for the selected Symbol type")
            self.callsign_display = self.get_district_display() + ' ' + str(self.callsign)
        else:
            self.callsign_display = self.callsign

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
        return force_text("{} {}".format(self.registration, self.deviceid))


class LoggedPoint(BasePoint):
    device = models.ForeignKey(Device, on_delete=models.PROTECT)
    raw = models.TextField(editable=False)

    def __str__(self):
        return force_text("{} {}".format(self.device, self.seen))

    @classmethod
    def parse_sbd(cls, sbd):
        """
        Parses an sbd into a persisted LoggedPoint object, also handles duplicates.
        """
        device = Device.objects.get_or_create(deviceid=sbd["ID"])[0]
        if sbd.get("LG", 0) == 0 or sbd.get("LT", 0) == 0:
            # LOGGER.warning ("Bad geometry for {}, discarding".format(device))
            return None
        seen = timezone.make_aware(datetime.fromtimestamp(float(sbd['TU'])), pytz.timezone("UTC"))
        # Ignore any duplicate LoggedPoint objects (should only be for accidental duplicate harvests or historical devices).
        try:
            self, created = cls.objects.get_or_create(device=device, seen=seen)
        except Exception:
            LOGGER.exception("ERROR during get_or_create of LoggedPoint: device {}, seen {}".format(device, seen))
            return None
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
        else:
            LOGGER.info("LoggedPoint {} found to be a duplicate.".format(self))
        if self.device.seen is None or self.seen > self.device.seen:
            self.device.seen = self.seen
            self.device.point = self.point
            self.device.heading = self.heading
            self.device.velocity = self.velocity
            self.device.altitude = self.altitude
            self.device.message = self.message
            self.device.source_device_type = self.source_device_type
            self.device.deleted = False
            self.device.save()
        return self

    class Meta:
        unique_together = (("device", "seen"),)


class InvalidLoggedPoint(BasePoint):
    INVALID_RAW_DATA = 1
    INVALID_TIMESTAMP = 10
    INVALID_TIMESTAMP_FORMAT = 11
    FUTURE_DATA = 20
    CATEGORIES = (
        (INVALID_RAW_DATA, "Invalid Raw Data"),
        (INVALID_TIMESTAMP, "Invalid Timestamp"),
        (INVALID_TIMESTAMP_FORMAT, "Invalid Timestamp Format"),
        (FUTURE_DATA, "Future Data")
    )
    deviceid = models.CharField(max_length=32, null=True, db_index=True)
    device_id = models.IntegerField(null=True, db_index=True)
    raw = models.TextField(editable=False)
    category = models.CharField(max_length=32, choices=CATEGORIES)
    error_msg = models.TextField()
    created = models.DateTimeField(auto_now_add=True, db_index=True)


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
