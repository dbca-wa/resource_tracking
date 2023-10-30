import csv
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import logging
import pytz
import requests

from tracking import email_utils
from tracking.models import Device, LoggedPoint
from tracking.utils import (
    validate_latitude_longitude,
    parse_mp70_payload,
    parse_spot_message,
    parse_iriditrak_message,
    parse_dplus_payload,
    parse_tracplus_row,
)

LOGGER = logging.getLogger('tracking')
UTC = pytz.timezone("UTC")
AWST = pytz.timezone("Australia/Perth")


def harvest_tracking_email(device_type, purge_email=False):
    """Download and save tracking point emails.
    `device_type` should be one of: iriditrak, dplus, spot, mp70
    """
    imap = email_utils.get_imap()
    start = timezone.now()
    created = 0
    flagged = 0

    if device_type == "iriditrak":
        LOGGER.info("Harvesting IridiTRAK emails")
        status, uids = email_utils.email_get_unread(imap, settings.EMAIL_IRIDITRAK)
    elif device_type == "dplus":
        LOGGER.info("Harvesting DPlus emails")
        status, uids = email_utils.email_get_unread(imap, settings.EMAIL_DPLUS)
    elif device_type == "spot":
        LOGGER.info("Harvesting Spot emails")
        status, uids = email_utils.email_get_unread(imap, settings.EMAIL_SPOT)
    elif device_type == "mp70":
        LOGGER.info("Harvesting MP70 emails")
        status, uids = email_utils.email_get_unread(imap, settings.EMAIL_MP70)

    if status != "OK":
        LOGGER.error(f"Server response failure: {status}")
    LOGGER.info(f"Server lists {len(uids)} unread emails")

    if uids:
        for uid in uids:
            # Decode uid to a string if required.
            if isinstance(uid, bytes):
                uid = uid.decode("utf-8")

            # Fetch the email message.
            status, message = email_utils.email_fetch(imap, uid)
            if status != "OK":
                LOGGER.error(f"Server response failure on fetching email UID {uid}: {status}")
                continue

            # `result` will be a LoggedPoint, or None
            if device_type == "iriditrak":
                result = save_iriditrak(message)
            elif device_type == "dplus":
                result = save_dplus(message)
            elif device_type == "spot":
                result = save_spot(message)
            elif device_type == "mp70":
                result = save_mp70(message)

            if not result:
                flagged += 1
            else:
                created += 1

            # Optionally mark email as read and flag it for deletion.
            if purge_email:
                status, response = email_utils.email_mark_read(imap, uid)
                status, response = email_utils.email_delete(imap, uid)
                LOGGER.info(f"Flagged {flagged} emails")

    LOGGER.info(f"Created {created} tracking points")
    imap.close()
    imap.logout()

    delta = timezone.now() - start
    start = start.astimezone(AWST)
    LOGGER.info(f"Tracking point email harvest run at {start} for {delta.seconds}s")
    return True


def save_mp70(message):
    """For a passed-in MP70 email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.

    Returns a LoggedPoint object, or None.
    """
    payload = message.get_payload()
    data = parse_mp70_payload(payload)

    if not data:
        LOGGER.warning(f"Unable to parse MP70 message payload: {payload}")
        return None

    # Validate lat/lon values.
    if not validate_latitude_longitude(data["latitude"], data["longitude"]):
        LOGGER.warning(f"Bad geometry while parsing MP70 message from device {data['device_id']}: {data['latitude']}, {data['longitude']}")
        return False

    device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    seen = data["timestamp"]
    if not device.seen or device.seen < seen:
        device.seen = seen
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    point = f"POINT({data['longitude']} {data['latitude']})"
    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point, source_device_type="mp70")
    loggedpoint.heading = data["heading"]
    loggedpoint.velocity = data["velocity"]
    loggedpoint.altitude = data["altitude"]
    loggedpoint.save()

    return loggedpoint


def save_spot(message):
    """For a passed-in Spot email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.

    Returns a LoggedPoint object, or None.
    """
    data = parse_spot_message(message)

    if not data:
        LOGGER.warning(f"Unable to parse Spot message: {message['SUBJECT']}")
        return None

    # Validate lat/lon values.
    if not validate_latitude_longitude(data["latitude"], data["longitude"]):
        LOGGER.warning(f"Bad geometry while parsing Spot message from device {data['device_id']}: {data['latitude']}, {data['longitude']}")
        return False

    device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    seen = data["timestamp"]
    if not device.seen or device.seen < seen:
        device.seen = seen
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    point = f"POINT({data['longitude']} {data['latitude']})"
    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point, source_device_type="spot")
    loggedpoint.heading = data["heading"]
    loggedpoint.velocity = data["velocity"]
    loggedpoint.altitude = data["altitude"]
    loggedpoint.save()

    return loggedpoint


def save_iriditrak(message):
    """For a passed-in Iriditrak email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.

    Returns a LoggedPoint object, or None.
    """
    data = parse_iriditrak_message(message)

    if not data:
        LOGGER.warning(f"Unable to parse Iriditrak message: {message['SUBJECT']}")
        return None

    # Validate lat/lon values.
    if not validate_latitude_longitude(data["latitude"], data["longitude"]):
        LOGGER.warning(f"Bad geometry while parsing Iriditrak message from device {data['device_id']}: {data['latitude']}, {data['longitude']}")
        return False

    device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    seen = data["timestamp"]
    if not device.seen or device.seen < seen:
        device.seen = seen
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    point = f"POINT({data['longitude']} {data['latitude']})"
    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point, source_device_type="iriditrak")
    loggedpoint.heading = data["heading"]
    loggedpoint.velocity = data["velocity"]
    loggedpoint.altitude = data["altitude"]
    loggedpoint.save()

    return loggedpoint


def save_dplus(message):
    """NOTE: DPlus tracking devices are no longer in active usage.
    For a passed-in DPlus email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.

    Returns a LoggedPoint object, or None.
    """
    payload = message.get_payload()
    data = parse_dplus_payload(message)

    if not data:
        LOGGER.warning(f"Unable to parse DPlus message payload: {payload}")
        return None

    # Validate lat/lon values.
    if not validate_latitude_longitude(data["latitude"], data["longitude"]):
        LOGGER.warning(f"Bad geometry while parsing DPlus message from device {data['device_id']}: {data['latitude']}, {data['longitude']}")
        return False

    device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    seen = data["timestamp"]
    if not device.seen or device.seen < seen:
        device.seen = seen
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    point = f"POINT({data['longitude']} {data['latitude']})"
    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point, source_device_type="dplus")
    loggedpoint.heading = data["heading"]
    loggedpoint.velocity = data["velocity"]
    loggedpoint.altitude = data["altitude"]
    loggedpoint.save()

    return loggedpoint


def save_dfes_feed():
    if not settings.DFES_URL:
        return

    LOGGER.info("Querying DFES API")
    resp = requests.get(url=settings.DFES_URL, auth=(settings.DFES_USER, settings.DFES_PASS))
    resp.raise_for_status()
    features = resp.json()["features"]
    LOGGER.info(f"DFES API returned {len(features)} features, processing")

    updated_device = 0
    created_device = 0
    skipped_device = 0

    for row in features:
        if row["type"] == "Feature":
            properties = row["properties"]
            geometry = row["geometry"]

            if "Time" not in properties or properties["Time"] is None:
                skipped_device += 1
                continue

            deviceid = str(properties["TrackerID"]).strip()
            device, created = Device.objects.get_or_create(source_device_type="dfes", deviceid=deviceid)

            # Parse the timestamp (returns as UTC timestamp).
            seen = UTC.localize(datetime.strptime(properties["Time"], "%Y-%m-%dT%H:%M:%S.%fZ"))

            # Parse the geometry.
            point = "POINT ({} {})".format(geometry["coordinates"][0], row["geometry"]["coordinates"][1])

            if created:
                created_device += 1
                device.callsign = properties["VehicleName"]
                device.callsign_display = properties["VehicleName"]
                device.model = properties["Model"]
                device.registration = "DFES - " + properties["Registration"][:32]
                device.symbol = (properties["VehicleType"]).strip()
                if device.symbol in [
                    "2.4 BROADACRE",
                    "2.4 RURAL",
                    "3.4",
                    "4.4",
                    "1.4 RURAL",
                    "2.4 URBAN",
                    "3.4 RURAL",
                    "3.4 SSSBFT",
                    "3.4 URBAN",
                    "4.4 BROADACRE",
                    "4.4 RURAL",
                ]:
                    device.symbol = "gang truck"
                elif device.symbol == "LIGHT TANKER":
                    device.symbol = "light unit"
                elif device.symbol in [
                    "BUS 10 SEATER",
                    "BUS 21 SEATER",
                    "BUS 22 SEATER",
                    "INCIDENT CONTROL VEHICLE",
                    "MINI BUS 12 SEATER",
                ]:
                    device.symbol = "comms bus"
                elif device.symbol in [
                    "GENERAL RESCUE TRUCK",
                    "HAZMAT STRUCTURAL RESCUE",
                    "RESCUE VEHICLE",
                    "ROAD CRASH RESCUE TRUCK",
                    "SPECIALIST EQUIPMENT TENDER",
                    "TRUCK",
                ]:
                    device.symbol = "tender"
                elif device.symbol in [
                    "Crew Cab Utility w canopy",
                    "FIRST RESPONSE UNIT",
                    "FIRST RESPONSE VEHICLE",
                    "UTILITY",
                    "Utility",
                ]:
                    device.symbol = "4 wheel drive ute"
                elif device.symbol in [
                    "CAR (4WD)",
                    "PERSONNEL CARRIER",
                    "PERSONNEL CARRIER 11 SEATER",
                    "PERSONNEL CARRIER 5 SEATER",
                    "PERSONNEL CARRIER 6 SEATER",
                ]:
                    device.symbol = "4 wheel drive passenger"
                elif device.symbol == "CAR":
                    device.symbol = "2 wheel drive"
                else:
                    device.symbol = "unknown"
                if device.registration.strip() == "DFES -":
                    device.registration = "DFES - No Rego"
                device.save()
            else:
                updated_device += 1

            if not device.seen or device.seen < seen:
                device.seen = seen
                device.point = point
                device.velocity = int(properties["Speed"]) * 1000
                device.heading = properties["Direction"]
                device.save()

            # Create a new LoggedPoint, if required.
            if not LoggedPoint.objects.filter(device=device, seen=seen, point=point, source_device_type="dfes").exists():
                LoggedPoint.objects.create(
                    device=device,
                    seen=seen,
                    point=point,
                    source_device_type="dfes",
                    velocity=int(properties["Speed"]) * 1000,
                    heading=properties["Direction"],
                )

    LOGGER.info(f"Created {created_device}, updated {updated_device}, skipped {skipped_device}")


def save_tracplus_feed():
    """Query the TracPlus API, create logged points per device.
    """
    if not settings.TRACPLUS_URL:
        return False

    LOGGER.info("Harvesting TracPlus feed")
    content = requests.get(settings.TRACPLUS_URL).content.decode("utf-8")
    latest = list(csv.DictReader(content.split("\r\n")))
    LOGGER.info(f"{len(latest)} records downloaded")
    created_device = 0
    updated_device = 0
    tracplus_symbol_map = {
        "Aircraft": "spotter aircraft",
        "Helicopter": "rotary aircraft",
    }

    for row in latest:
        data = parse_tracplus_row(row)

        if not data:
            LOGGER.warning(f"Unable to parse TracPlus feed row: {row['Report ID']}")
            return None

        # Validate lat/lon values.
        if not validate_latitude_longitude(data["latitude"], data["longitude"]):
            LOGGER.warning(f"Bad geometry while parsing TracPlus data from device {data['device_id']}: {data['latitude']}, {data['longitude']}")
            return False

        device, created = Device.objects.get_or_create(deviceid=data["device_id"])
        if created:
            created_device += 1
            device.source_device_type = "tracplus"
            # Set some additional values on the Device from the CSV row data.
            device.callsign = row["Asset Name"]
            device.callsign_display = row["Asset Name"]
            device.model = row["Asset Model"]
            device.registration = row["Asset Regn"][:32]
            if row["Asset Type"] in tracplus_symbol_map:
                device.symbol = tracplus_symbol_map[row["Asset Type"]]
            device.save()
        else:
            updated_device += 1

        seen = data["timestamp"]
        if not device.seen or device.seen < seen:
            device.seen = seen
            device.heading = data["heading"]
            device.velocity = data["velocity"]
            device.altitude = data["altitude"]
            device.save()

        point = f"POINT({data['longitude']} {data['latitude']})"
        loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point, source_device_type="tracplus")
        loggedpoint.heading = data["heading"]
        loggedpoint.velocity = data["velocity"]
        loggedpoint.altitude = data["altitude"]
        loggedpoint.save()

    LOGGER.info(f"Updated {updated_device} TracPlus devices, created {created_device} devices")
