import logging

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.gis.db import models
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.validators import MaxValueValidator
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.forms import ValidationError
from django.utils import timezone

LOGGER = logging.getLogger("tracking")


DISTRICT_PERTH_HILLS = "PHD"
DISTRICT_SWAN_COASTAL = "SCD"
DISTRICT_SWAN_REGION = "SWAN"
DISTRICT_BLACKWOOD = "BWD"
DISTRICT_WELLINGTON = "WTN"
DISTRICT_SOUTH_WEST_REGION = "SWR"
DISTRICT_DONNELLY = "DON"
DISTRICT_FRANKLAND = "FRK"
DISTRICT_WARREN_REGION = "WR"
DISTRICT_ALBANY = "ALB"
DISTRICT_ESPERANCE = "ESP"
DISTRICT_SOUTH_COAST_REGION = "SCR"
DISTRICT_EAST_KIMBERLEY = "EKD"
DISTRICT_WEST_KIMBERLEY = "WKD"
DISTRICT_KIMBERLEY_REGION = "KIMB"
DISTRICT_PILBARA_REGION = "PIL"
DISTRICT_EXMOUTH = "EXM"
DISTRICT_GOLDFIELDS_REGION = "GLD"
DISTRICT_GERALDTON = "GER"
DISTRICT_KALBARRI = "KLB"
DISTRICT_MOORA = "MOR"
DISTRICT_SHARK_BAY = "SHB"
DISTRICT_MIDWEST_REGION = "MWR"
DISTRICT_CENTRAL_WHEATBELT = "CWB"
DISTRICT_SOUTHERN_WHEATBELT = "SWB"
DISTRICT_WHEATBELT_REGION = "WBR"
DISTRICT_AVIATION = "AV"
DISTRICT_OTHER = "OTH"

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
    (DISTRICT_OTHER, "Other"),
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
    ("unknown", "Unknown"),
)

RAW_EQ_CHOICES = (
    (1, "Accessories Turned ON Message"),
    (2, "Accessories Turned OFF Message"),
    (3, "Tracking Message"),
    (5, "Remote Polling Message"),
    (18, "Emergency Message"),
    (19, "Remote Command Acknowledge for Emergency Turn Off"),
    (25, "Start Moving"),
    (26, "Stop Moving"),
)

SOURCE_DEVICE_TYPE_CHOICES = (
    ("tracplus", "TracPlus"),
    ("iriditrak", "Iriditrak"),
    ("dplus", "DPlus"),
    ("spot", "Spot"),
    ("dfes", "DFES"),
    ("mp70", "MP70"),
    ("fleetcare", "Fleetcare"),
    ("other", "Other"),
)


class Device(models.Model):
    """A location-tracking device installed in a vehicle for the purposes of monitoring its location
    and heading over time, plus metadata about the vehicle itself.
    """

    deviceid = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Device ID",
        help_text="Device unique identifier",
    )
    registration = models.CharField(max_length=32, default="No Rego", help_text="e.g. 1QBB157")
    rin_number = models.PositiveIntegerField(
        validators=[MaxValueValidator(999)],
        verbose_name="Resource Identification Number (RIN)",
        null=True,
        blank=True,
        help_text="Heavy Duty, Gang Truck or Plant only (HD/GT/P automatically prefixed).",
    )
    rin_display = models.CharField(max_length=5, null=True, blank=True, verbose_name="RIN")
    symbol = models.CharField(max_length=32, choices=SYMBOL_CHOICES, default="other")
    district = models.CharField(
        max_length=32,
        choices=DISTRICT_CHOICES,
        default=DISTRICT_OTHER,
        verbose_name="Region/District",
    )
    district_display = models.CharField(max_length=100, default="Other", verbose_name="District")
    usual_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. John Jones")
    usual_location = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Karijini National Park")
    current_driver = models.CharField(max_length=50, null=True, blank=True, help_text="e.g. Jodie Jones")
    callsign = models.CharField(max_length=50, null=True, blank=True, help_text="")
    callsign_display = models.CharField(max_length=50, null=True, blank=True, verbose_name="Callsign")
    contractor_details = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Person engaging contractor is responsible for maintaining contractor resource details",
    )
    other_details = models.TextField(null=True, blank=True)
    internal_only = models.BooleanField(
        default=False,
        help_text="Device will only be shown on internal DBCA resource tracking live view (not to DFES, etc.)",
    )
    hidden = models.BooleanField(default=False, help_text="Device hidden from DBCA resource tracking live view")
    deleted = models.BooleanField(default=False, verbose_name="Deleted?")
    fire_use = models.BooleanField(default=None, null=True, verbose_name="Fire use")

    seen = models.DateTimeField(null=True, editable=False)
    point = models.PointField(null=True, editable=False)

    heading = models.PositiveIntegerField(default=0, help_text="Heading in degrees", editable=False)
    velocity = models.PositiveIntegerField(default=0, help_text="Speed in metres/hr", editable=False)
    altitude = models.IntegerField(default=0, help_text="Altitude above sea level in metres", editable=False)
    message = models.PositiveIntegerField(default=3, choices=RAW_EQ_CHOICES)
    source_device_type = models.CharField(
        max_length=32,
        choices=SOURCE_DEVICE_TYPE_CHOICES,
        default="other",
        db_index=True,
    )

    class Meta:
        ordering = ("-seen",)

    def __str__(self):
        return f"{self.registration} {self.deviceid}"

    @property
    def age_minutes(self):
        if not self.seen:
            return None
        delta = timezone.now() - self.seen
        minutes = delta.days * 24 * 60 + delta.seconds // 60
        return minutes

    @property
    def age_colour(self):
        if not self.seen:
            return "red"
        minutes = self.age_minutes
        if minutes < 60:
            return "green"
        elif minutes < 180:
            return "orange"
        else:
            return "red"

    @property
    def age_text(self):
        # Returns age in humanized form
        return naturaltime(self.seen).replace("\xa0", " ")

    @property
    def icon(self):
        return "sss-{}".format(self.symbol.lower().replace(" ", "_"))

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.district:
            self.district_display = self.get_district_display()
        if self.callsign:
            self.callsign_display = self.callsign
        if self.rin_number:
            if self.symbol == "heavy duty":
                symbol_prefix = "HD"
            elif self.symbol == "gang truck":
                symbol_prefix = "GT"
            elif self.symbol in ("grader", "dozer", "loader", "tender", "float"):
                symbol_prefix = "P"
            else:
                symbol_prefix = ""
            self.rin_display = f"{symbol_prefix}{self.rin_number}"
        else:
            self.rin_display = None
        super().save(force_insert, force_update)

    def clean(self):
        # Clean rin_number
        if self.rin_number and self.symbol not in (
            "heavy duty",
            "gang truck",
            "dozer",
            "grader",
            "loader",
            "tender",
            "float",
        ):
            raise ValidationError(
                "Please remove the RIN number or select a symbol from Heavy Duty, Gang Truck, Dozer, Grader, Loader, Tender or Float"
            )
        if not self.rin_number and self.symbol in (
            "heavy duty",
            "gang truck",
            "dozer",
            "grader",
            "loader",
            "tender",
            "float",
        ):
            raise ValidationError("Please enter a RIN number")


class LoggedPoint(models.Model):
    """An instance of the location of a tracking device at a point in time, plus additional metadata
    where available.
    """

    device = models.ForeignKey(Device, on_delete=models.PROTECT)
    seen = models.DateTimeField(editable=False, db_index=True)
    point = models.PointField(editable=False)
    heading = models.PositiveIntegerField(default=0, help_text="Heading in degrees", editable=False)
    velocity = models.PositiveIntegerField(default=0, help_text="Speed in metres/hr", editable=False)
    altitude = models.IntegerField(default=0, help_text="Altitude above sea level in metres", editable=False)
    message = models.PositiveIntegerField(default=3, choices=RAW_EQ_CHOICES)
    source_device_type = models.CharField(
        max_length=32,
        choices=SOURCE_DEVICE_TYPE_CHOICES,
        default="other",
        db_index=True,
    )

    raw = models.TextField(editable=False, null=True, blank=True)

    def __str__(self):
        return f"{self.device} {self.seen.astimezone(settings.TZ)}"

    class Meta:
        ordering = ("-seen",)
        unique_together = (("device", "seen"),)


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # Set is_staff to True so users can edit Device details
    instance.is_staff = True


@receiver(post_save, sender=User)
def user_post_save(sender, instance, **kwargs):
    # Add users to the 'Edit Resource Tracking Device' group so users can edit Device details
    # NOTE: does not work when saving user in Django Admin
    g, created = Group.objects.get_or_create(name="Edit Resource Tracking Device")
    instance.groups.add(g)
