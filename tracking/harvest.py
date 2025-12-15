import csv
import logging
from email.message import EmailMessage
from imaplib import IMAP4
from typing import Literal

import requests
from django.conf import settings
from django.utils import timezone

from tracking import email_utils
from tracking.models import Device, LoggedPoint
from tracking.utils import (
    SanitizingJSONDecoder,
    parse_dfes_feature,
    parse_dplus_payload,
    parse_iriditrak_message,
    parse_mp70_payload,
    parse_netstar_feature,
    parse_spot_message,
    parse_tracertrak_feature,
    parse_tracplus_row,
    parse_zoleo_payload,
    validate_latitude_longitude,
)

LOGGER = logging.getLogger("tracking")


def harvest_tracking_email(device_type, purge_email=False):
    """Download and save tracking point emails.
    `device_type` should be one of: iriditrak, dplus, spot, mp70, zoleo
    """
    imap = email_utils.get_imap()
    if not imap:
        LOGGER.warning("Mailbox not available")
        return

    start = timezone.now()
    created = 0
    flagged = 0
    unread_emails = None

    if device_type == "iriditrak":
        LOGGER.info("Harvesting IridiTRAK emails")
        unread_emails = email_utils.email_get_unread(imap, settings.EMAIL_IRIDITRAK)
    elif device_type == "dplus":
        LOGGER.info("Harvesting DPlus emails")
        unread_emails = email_utils.email_get_unread(imap, settings.EMAIL_DPLUS)
    elif device_type == "spot":
        LOGGER.info("Harvesting Spot emails")
        unread_emails = email_utils.email_get_unread(imap, settings.EMAIL_SPOT)
    elif device_type == "mp70":
        LOGGER.info("Harvesting MP70 emails")
        unread_emails = email_utils.email_get_unread(imap, settings.EMAIL_MP70)
    elif device_type == "zoleo":
        LOGGER.info("Harvesting Zoleo emails")
        unread_emails = email_utils.email_get_unread(imap, settings.EMAIL_ZOLEO)

    if not unread_emails:
        LOGGER.warning("Mail server status failure")
        return

    status, uids = unread_emails
    if status != "OK":
        LOGGER.warning(f"Mail server status failure: {status}")
        return

    LOGGER.info(f"Server lists {len(uids)} unread emails")

    if uids:
        for uid in uids:
            # Decode uid to a string if required.
            if isinstance(uid, bytes):
                uid = uid.decode("utf-8")

            # Fetch the email message.
            email_message = email_utils.email_fetch(imap, uid)
            if not email_message:
                LOGGER.warning(f"Mail server status failure on fetching email UID {uid}")
                continue

            status, message = email_message
            if status != "OK" or not message:
                LOGGER.warning(f"Mail server status failure on fetching email UID {uid}: {status}")
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
            elif device_type == "zoleo":
                result = save_zoleo(message)
            else:
                result = None

            if result:
                created += 1
            elif not result and purge_email:
                flagged += 1

            # Optionally mark email as read and flag it for deletion.
            if purge_email:
                email_utils.email_mark_read(imap, uid)
                email_utils.email_delete(imap, uid)

    LOGGER.info(f"Created {created} tracking points, flagged {flagged} emails")

    try:
        imap.close()
        imap.logout()
    except IMAP4.abort:
        LOGGER.warning("IMAP abort")
        pass

    delta = timezone.now() - start
    start = start.astimezone(settings.TZ)
    LOGGER.info(f"Tracking point email harvest run at {start} for {delta.seconds}s")
    return True


def save_mp70(message: EmailMessage) -> LoggedPoint | Literal[None, False]:
    """For a passed-in MP70 email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.
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

    try:
        device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    except Exception as e:
        LOGGER.warning(f"Exception during creation/query of MP70 device: {data}")
        LOGGER.error(e)
        return False

    if created:
        device.source_device_type = "mp70"

    seen = data["timestamp"]
    point = f"POINT({data['longitude']} {data['latitude']})"

    if not device.seen or device.seen < seen:
        device.seen = seen
        device.point = point
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
    if created:
        loggedpoint.source_device_type = "mp70"
        loggedpoint.heading = data["heading"]
        loggedpoint.velocity = data["velocity"]
        loggedpoint.altitude = data["altitude"]
        loggedpoint.save()

    return loggedpoint


def save_spot(message: EmailMessage) -> LoggedPoint | Literal[None, False]:
    """For a passed-in Spot email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.
    """
    data = parse_spot_message(message)

    if not data:
        LOGGER.warning(f"Unable to parse Spot message: {message['SUBJECT']}")
        return None

    # Validate lat/lon values.
    if not validate_latitude_longitude(data["latitude"], data["longitude"]):
        LOGGER.warning(f"Bad geometry while parsing Spot message from device {data['device_id']}: {data['latitude']}, {data['longitude']}")
        return False

    try:
        device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    except Exception as e:
        LOGGER.warning(f"Exception during creation/query of Spot device: {data}")
        LOGGER.error(e)
        return False

    if created:
        device.source_device_type = "spot"
        device.symbol = "person"

    seen = data["timestamp"]
    point = f"POINT({data['longitude']} {data['latitude']})"

    if not device.seen or device.seen < seen:
        device.seen = seen
        device.point = point
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
    if created:
        loggedpoint.source_device_type = "spot"
        loggedpoint.heading = data["heading"]
        loggedpoint.velocity = data["velocity"]
        loggedpoint.altitude = data["altitude"]
        loggedpoint.save()

    return loggedpoint


def save_iriditrak(message: EmailMessage) -> LoggedPoint | Literal[None, False]:
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
        LOGGER.warning(
            f"Bad geometry while parsing Iriditrak message from device {data['device_id']}: {data['latitude']}, {data['longitude']}"
        )
        return False

    try:
        device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    except Exception as e:
        LOGGER.warning(f"Exception during creation/query of Iriditrak device: {data}")
        LOGGER.error(e)
        return False

    if created:
        device.source_device_type = "iriditrak"

    seen = data["timestamp"]
    point = f"POINT({data['longitude']} {data['latitude']})"

    if not device.seen or device.seen < seen:
        device.seen = seen
        device.point = point
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
    if created:
        loggedpoint.source_device_type = "iriditrak"
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

    try:
        device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    except Exception as e:
        LOGGER.warning(f"Exception during creation/query of DPlus device: {data}")
        LOGGER.error(e)
        return False

    if created:
        device.source_device_type = "dplus"

    seen = data["timestamp"]
    point = f"POINT({data['longitude']} {data['latitude']})"

    if not device.seen or device.seen < seen:
        device.seen = seen
        device.point = point
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
    if created:
        loggedpoint.source_device_type = "dplus"
        loggedpoint.heading = data["heading"]
        loggedpoint.velocity = data["velocity"]
        loggedpoint.altitude = data["altitude"]
        loggedpoint.save()

    return loggedpoint


DFES_SYMBOL_MAP = {
    "2.4 BROADACRE": "gang truck",
    "2.4 RURAL": "gang truck",
    "3.4": "gang truck",
    "4.4": "gang truck",
    "1.4 RURAL": "gang truck",
    "2.4 URBAN": "gang truck",
    "3.4 RURAL": "gang truck",
    "3.4 SSSBFT": "gang truck",
    "3.4 URBAN": "gang truck",
    "4.4 BROADACRE": "gang truck",
    "4.4 RURAL": "gang truck",
    "LIGHT TANKER": "light unit",
    "BUS 10 SEATER": "comms bus",
    "BUS 21 SEATER": "comms bus",
    "BUS 22 SEATER": "comms bus",
    "INCIDENT CONTROL VEHICLE": "comms bus",
    "MINI BUS 12 SEATER": "comms bus",
    "GENERAL RESCUE TRUCK": "tender",
    "HAZMAT STRUCTURAL RESCUE": "tender",
    "RESCUE VEHICLE": "tender",
    "ROAD CRASH RESCUE TRUCK": "tender",
    "SPECIALIST EQUIPMENT TENDER": "tender",
    "TRUCK": "tender",
    "Crew Cab Utility w canopy": "4 wheel drive ute",
    "FIRST RESPONSE UNIT": "4 wheel drive ute",
    "FIRST RESPONSE VEHICLE": "4 wheel drive ute",
    "UTILITY": "4 wheel drive ute",
    "Utility": "4 wheel drive ute",
    "CAR (4WD)": "4 wheel drive passenger",
    "PERSONNEL CARRIER": "4 wheel drive passenger",
    "PERSONNEL CARRIER 11 SEATER": "4 wheel drive passenger",
    "PERSONNEL CARRIER 5 SEATER": "4 wheel drive passenger",
    "PERSONNEL CARRIER 6 SEATER": "4 wheel drive passenger",
    "CAR": "2 wheel drive",
}


def save_dfes_feed():
    """Download and process the DFES API endpoint (returns GeoJSON), create new devices, update existing."""
    LOGGER.info("Querying DFES API")
    try:
        resp = requests.get(url=settings.DFES_URL, auth=(settings.DFES_USER, settings.DFES_PASS))
    except (requests.ConnectionError, requests.Timeout) as err:
        LOGGER.warning(f"Connection error: {err}")
        return

    # Don't raise an exception on non-200 response.
    if not resp.status_code == 200:
        LOGGER.warning("DFES API response returned non-200 status")
        return

    # Parse the API response.
    try:
        features = resp.json(cls=SanitizingJSONDecoder)["features"]
    except requests.models.JSONDecodeError as err:
        LOGGER.warning(f"Error parsing DFES API response: {err.doc}")
        return

    LOGGER.info(f"DFES API returned {len(features)} features, processing")

    updated_device = 0
    created_device = 0
    skipped_device = 0
    logged_points = 0

    for feature in features:
        data = parse_dfes_feature(feature)

        if not data:
            LOGGER.warning(f"Unable to parse DFES feed feature: {feature['id']}")
            skipped_device += 1
            continue

        # Skip archived, decommissioned vehicles.
        if data["vehicle_group"] in ["Decommissioned", "Archive"]:
            skipped_device += 1
            continue

        # Validate lat/lon values.
        if not validate_latitude_longitude(data["latitude"], data["longitude"]):
            LOGGER.warning(f"Bad geometry while parsing data for DFES device {data['device_id']}: {data['latitude']}, {data['longitude']}")
            skipped_device += 1
            continue

        try:
            device, created = Device.objects.get_or_create(deviceid=data["device_id"])
        except Exception as e:
            LOGGER.warning(f"Exception during creation/query of DFES device: {data}")
            LOGGER.error(e)
            continue

        properties = feature["properties"]

        if created:
            created_device += 1
            device.source_device_type = "dfes"
        else:
            updated_device += 1

        device.callsign = properties["VehicleName"]
        device.callsign_display = properties["VehicleName"]
        if properties["Registration"]:
            device.registration = properties["Registration"][:32].strip()
        if properties["VehicleType"].strip() in DFES_SYMBOL_MAP:
            device.symbol = DFES_SYMBOL_MAP[properties["VehicleType"].strip()]

        seen = data["timestamp"]
        point = f"POINT({data['longitude']} {data['latitude']})"

        if not device.seen or device.seen < seen:
            device.seen = seen
            device.point = point
            device.heading = data["heading"]
            device.velocity = data["velocity"]
            device.altitude = data["altitude"]

        device.save()

        loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
        if created:
            loggedpoint.source_device_type = "dfes"
            loggedpoint.heading = data["heading"]
            loggedpoint.velocity = data["velocity"]
            loggedpoint.altitude = data["altitude"]
            loggedpoint.save()
            logged_points += 1

    LOGGER.info(f"Created {created_device}, updated {updated_device}, skipped {skipped_device}, {logged_points} new logged points")


def save_tracplus_feed():
    """Query the TracPlus API, create logged points per device, update existing devices."""
    LOGGER.info("Harvesting TracPlus feed")
    try:
        resp = requests.get(settings.TRACPLUS_URL)
    except (requests.ConnectionError, requests.Timeout) as err:
        LOGGER.warning(f"Connection error: {err}")
        return

    # The TracPlus API frequently throttles requests.
    if resp.status_code == 429:
        LOGGER.warning("TracPlus API returned HTTP 429 Too Many Requests")
        return

    content = resp.content.decode("utf-8")
    # Split the content body on newline boundaries.
    lines = content.splitlines()
    latest = list(csv.DictReader(lines))
    LOGGER.info(f"{len(latest)} records downloaded, processing")

    created_device = 0
    updated_device = 0
    skipped_device = 0
    logged_points = 0
    tracplus_symbol_map = {
        "Aircraft": "spotter aircraft",
        "Helicopter": "rotary aircraft",
        "Person": "person",
        "Car": "2 wheel drive",
    }

    for row in latest:
        data = parse_tracplus_row(row)

        if not data:
            LOGGER.warning(f"Unable to parse TracPlus feed row: {row['Report ID']}")
            skipped_device += 1
            continue

        # Validate lat/lon values.
        if not validate_latitude_longitude(data["latitude"], data["longitude"]):
            LOGGER.warning(
                f"Bad geometry while parsing TracPlus data from device {data['device_id']}: {data['latitude']}, {data['longitude']}"
            )
            skipped_device += 1
            continue

        try:
            device, created = Device.objects.get_or_create(deviceid=data["device_id"])
        except Exception as e:
            LOGGER.warning(f"Exception during creation/query of TracPlus device: {row}")
            LOGGER.error(e)
            skipped_device += 1
            continue

        rego = row["Asset Regn"][:32].strip()
        symbol = tracplus_symbol_map[row["Asset Type"]] if row["Asset Type"] in tracplus_symbol_map else None

        if created:
            created_device += 1
            device.source_device_type = "tracplus"
        else:
            updated_device += 1

        device.registration = rego
        if symbol:
            device.symbol = symbol

        seen = data["timestamp"]
        point = f"POINT({data['longitude']} {data['latitude']})"

        if not device.seen or device.seen < seen:
            device.seen = seen
            device.point = point
            device.heading = data["heading"]
            device.velocity = data["velocity"]
            device.altitude = data["altitude"]

        device.save()

        loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
        if created:
            loggedpoint.source_device_type = "tracplus"
            loggedpoint.heading = data["heading"]
            loggedpoint.velocity = data["velocity"]
            loggedpoint.altitude = data["altitude"]
            loggedpoint.save()
            logged_points += 1

    LOGGER.info(
        f"Updated {updated_device} devices, created {created_device} devices, skipped {skipped_device} devices, {logged_points} new logged points"
    )


def save_tracertrak_feed():
    """Download and process the TracerTrack API endpoint (returns GeoJSON), create new devices, update existing."""
    LOGGER.info("Querying TracerTrak API")
    try:
        resp = requests.get(url=settings.TRACERTRAK_URL, params={"auth": settings.TRACERTRAK_AUTH_TOKEN})
    except (requests.ConnectionError, requests.Timeout) as err:
        LOGGER.warning(f"Connection error: {err}")
        return

    # Don't raise an exception on non-200 response.
    if not resp.status_code == 200:
        LOGGER.warning("TracerTrak API response returned non-200 status")
        return

    # Parse the API response.
    try:
        features = resp.json()["features"]
    except requests.models.JSONDecodeError as err:
        LOGGER.warning(f"Error parsing TracerTrak API response: {err.doc}")
        return

    LOGGER.info(f"TracerTrak API returned {len(features)} features, processing")

    updated_device = 0
    created_device = 0
    skipped_device = 0
    logged_points = 0

    for feature in features:
        data = parse_tracertrak_feature(feature)

        if not data:
            LOGGER.warning(f"Unable to parse TracerTrak feature: {feature['deviceID']}")
            skipped_device += 1
            continue

        # Validate lat/lon values.
        if not validate_latitude_longitude(data["latitude"], data["longitude"]):
            LOGGER.warning(
                f"Bad geometry while parsing data for TracerTrak device {data['device_id']}: {data['latitude']}, {data['longitude']}"
            )
            skipped_device += 1
            continue

        try:
            device, created = Device.objects.get_or_create(deviceid=data["device_id"])
        except Exception as e:
            LOGGER.warning(f"Exception during creation/query of TracerTrak device: {data}")
            LOGGER.error(e)
            continue

        properties = feature["properties"]

        if created:
            created_device += 1
            device.source_device_type = "tracertrak"
        else:
            updated_device += 1

        if "name" in properties:
            device.callsign = properties["name"]
            device.callsign_display = properties["name"]

        seen = data["timestamp"]
        point = f"POINT({data['longitude']} {data['latitude']})"

        if not device.seen or device.seen < seen:
            device.seen = seen
            device.point = point
            device.heading = data["heading"]
            device.velocity = data["velocity"]
            device.altitude = data["altitude"]

        device.save()

        loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
        if created:
            loggedpoint.heading = data["heading"]
            loggedpoint.velocity = data["velocity"]
            loggedpoint.altitude = data["altitude"]
            loggedpoint.source_device_type = "tracertrak"
            loggedpoint.save()
            logged_points += 1

    LOGGER.info(f"Created {created_device}, updated {updated_device}, skipped {skipped_device}, {logged_points} new logged points")


def save_netstar_feed():
    """Download the Netstar API feed (returns JSON, not valid GeoJSON) and create/update devices returned."""
    LOGGER.info("Querying Netstar API")
    try:
        resp = requests.get(url=settings.NETSTAR_URL, auth=(settings.NETSTAR_USER, settings.NETSTAR_PASS))
    except (requests.ConnectionError, requests.Timeout) as err:
        LOGGER.warning(f"Connection error: {err}")
        return

    # Don't raise an exception on non-200 response.
    if not resp.status_code == 200:
        LOGGER.warning(f"Netstar API response returned non-200 status: {resp.status_code}")
        return

    # Parse the API response.
    try:
        vehicles = resp.json()["Vehicles"]
    except requests.models.JSONDecodeError as err:
        LOGGER.warning(f"Error parsing Netstar API response: {err.doc}")
        return

    LOGGER.info(f"Netstar API returned {len(vehicles)} vehicles, processing")

    updated_device = 0
    created_device = 0
    skipped_device = 0
    logged_points = 0

    for vehicle in vehicles:
        data = parse_netstar_feature(vehicle)

        if not data:
            LOGGER.warning(f"Unable to parse Netstar feed feature: {vehicle['TrackerID']}")
            skipped_device += 1
            continue

        # Validate lat/lon values.
        if not validate_latitude_longitude(data["latitude"], data["longitude"]):
            LOGGER.warning(
                f"Bad geometry while parsing data for Netstar device {vehicle['TrackerID']}: {data['latitude']}, {data['longitude']}"
            )
            skipped_device += 1
            continue

        try:
            device, created = Device.objects.get_or_create(deviceid=f"ns_{data['device_id']}")
        except Exception as e:
            LOGGER.warning(f"Exception during creation/query of Netstar device: {data}")
            LOGGER.error(e)
            continue

        if created:
            created_device += 1
            device.source_device_type = "netstar"
        else:
            updated_device += 1

        device.registration = data["registration"]
        seen = data["timestamp"]
        point = f"POINT({data['longitude']} {data['latitude']})"

        if not device.seen or device.seen < seen:
            device.seen = seen
            device.point = point

        device.save()

        loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
        if created:
            loggedpoint.source_device_type = "netstar"
            loggedpoint.save()
            logged_points += 1

    LOGGER.info(f"Created {created_device}, updated {updated_device}, skipped {skipped_device}, {logged_points} new logged points")


def save_zoleo(message: EmailMessage) -> LoggedPoint | Literal[None, False]:
    """For a passed-in Zoleo email message, parse the payload, get/create a Device,
    set the device 'seen' value, and create a LoggedPoint.
    """
    data = parse_zoleo_payload(message)

    if not data:
        LOGGER.warning(f"Unable to parse Zoleo message: {message['SUBJECT']}")
        return None

    # Validate lat/lon values.
    if not validate_latitude_longitude(data["latitude"], data["longitude"]):
        LOGGER.warning(
            f"Bad geometry while parsing Zoleo check-in message from device {data['device_id']}: {data['latitude']}, {data['longitude']}"
        )
        return False

    try:
        device, created = Device.objects.get_or_create(deviceid=data["device_id"])
    except Exception as e:
        LOGGER.warning(f"Exception during creation/query of Zoleo device: {data}")
        LOGGER.error(e)
        return False

    if created:
        device.source_device_type = "zoleo"
        device.symbol = "person"

    seen = data["timestamp"]
    point = f"POINT({data['longitude']} {data['latitude']})"

    if not device.seen or device.seen < seen:
        device.seen = seen
        device.point = point
        device.heading = data["heading"]
        device.velocity = data["velocity"]
        device.altitude = data["altitude"]
        device.save()

    loggedpoint, created = LoggedPoint.objects.get_or_create(device=device, seen=seen, point=point)
    if created:
        loggedpoint.source_device_type = "zoleo"
        loggedpoint.heading = data["heading"]
        loggedpoint.velocity = data["velocity"]
        loggedpoint.altitude = data["altitude"]
        loggedpoint.raw = data["raw"]
        loggedpoint.save()

    return loggedpoint
