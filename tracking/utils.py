import json
import re
import struct
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parsedate
from html import unescape
from typing import Any, Dict, List, Literal

from django.core.paginator import Page
from fudgeo.constant import WGS84
from fudgeo.geopkg import SpatialReferenceSystem

SRS_WKT = """GEOGCS["WGS 84",
    DATUM["WGS_1984",
        SPHEROID["WGS 84",6378137,298.257223563,
            AUTHORITY["EPSG","7030"]],
        AUTHORITY["EPSG","6326"]],
    PRIMEM["Greenwich",0,
        AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.0174532925199433,
        AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]"""


def get_srs_wgs84() -> SpatialReferenceSystem:
    return SpatialReferenceSystem(name="WGS 84", organization="EPSG", org_coord_sys_id=WGS84, definition=SRS_WKT)


def validate_latitude_longitude(latitude: float, longitude: float) -> bool:
    """Validate passed-in latitude and longitude values."""
    # Both latitude and longitude equalling zero is considered invalid.
    if latitude == 0.0 and longitude == 0.0:
        return False

    return latitude <= 90 and latitude >= -90 and longitude <= 180 and longitude >= -180


def parse_zoleo_message(message: EmailMessage):
    """Parse the email body content of a Zoleo check-in message for a location."""
    # First, obtain just the lines of interest from the email content (the check-in).
    body = message.get_body(preferencelist=("plain",))
    if not body:  # Null body content
        return False
    content = body.get_content()
    content_lines = [line.strip() for line in content.splitlines()]
    checkin_lines = []
    save = False
    for line in content_lines:
        if line == "<!-- Check In -->":
            save = True
        elif line.startswith("<!--"):
            save = False
        if save:
            checkin_lines.append(unescape(line).replace("<br />", ""))

    if not checkin_lines:
        return False

    # Parse the device_id, coordinates and timestamp from the check-in lines.
    device_id = None
    latitude = None
    longitude = None
    timestamp = None

    try:
        for line in checkin_lines:
            if line.startswith("Device:"):
                pattern = r"^Device:\s(?P<device_id>.+$)"
                device_match = re.search(pattern, line)
                if device_match:
                    d = device_match.groupdict()
                    if "device_id" in d:
                        device_id = d["device_id"]

            if line.startswith("Message:"):
                pattern = r"(?P<latitude>-?\d+\.\d+),\s+(?P<longitude>-?\d+\.\d+)"
                coords_match = re.search(pattern, line)
                if coords_match:
                    d = coords_match.groupdict()
                    if "latitude" in d:
                        latitude = d["latitude"]
                    if "longitude" in d:
                        longitude = d["longitude"]

            if line.startswith("Check-in sent at:"):
                pattern = r"^Check-in sent at:\s(?P<timestamp>.+$)"
                timestamp_match = re.search(pattern, line)
                if timestamp_match:
                    d = timestamp_match.groupdict()
                    if "timestamp" in d:
                        timestamp = d["timestamp"]

        if not device_id or not latitude or not longitude or not timestamp:
            return False

        timetuple = parsedate(timestamp)
        timestamp = time.mktime(timetuple)  # Timestamp integer.
        # Assume timestamp is UTC, cast timestamp as a datetime object.
        timestamp = datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)

        return {
            "device_id": device_id,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "velocity": 0,
            "heading": 0,
            "altitude": 0,
            "timestamp": timestamp,
            "type": "zoleo",
        }
    except:
        return False


def parse_mp70_payload(payload: str) -> Dict | Literal[False]:
    """Parses a passed-in MP70 email payload. Returns a dict or False.

    MP70 payloads consist of comma-separated data values:
    Device_ID, Battery_Voltage, Latitude, Longitude, Speed_km/h, Heading, Time_UTC
    """
    # First, remove newline characters and split on commas.
    # If we can't parse the raw payload, return False.
    try:
        payload = payload.replace("=\r\n", "").strip().split(",")
    except:
        return False

    # Next, cast the payload elements as the correct types.
    # If we can't cast the types, return False.
    try:
        data = {
            "device_id": payload[0],
            "battery_voltage": payload[1],
            "latitude": float(payload[2]),
            "longitude": float(payload[3]),
            "velocity": int(payload[4]),
            "heading": int(payload[5]),
            "altitude": 0,
            "timestamp": datetime.strptime(payload[6], "%m/%d/%Y %H:%M:%S").replace(tzinfo=timezone.utc),
            "type": "mp70",
        }
    except:
        return False

    return data


def parse_spot_message(message: EmailMessage) -> Dict | Literal[False]:
    """Parses the passed-in Spot email message. Returns a dict or False."""
    try:
        # Ref: https://docs.python.org/3.11/library/email.utils.html#email.utils.parsedate
        timetuple = parsedate(message["DATE"])
        timestamp = time.mktime(timetuple)  # Timestamp integer.
        # Assume timestamp is UTC, cast timestamp as a datetime object.
        timestamp = datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)
        data = {
            "device_id": message["X-SPOT-Messenger"],
            "latitude": float(message["X-SPOT-Latitude"]),
            "longitude": float(message["X-SPOT-Longitude"]),
            "velocity": 0,
            "heading": 0,
            "altitude": 0,
            "timestamp": timestamp,
            "type": "spot",
        }
    except:
        return False

    return data


def parse_beam_payload(attachment: bytes) -> Dict | Literal[False]:
    """Attempt to parse the binary attachment for tracking data. Returns a dict or False.
    Reference: https://www.beamcommunications.com/document/342-beam-message-format
    """
    beam = dict()
    raw = struct.unpack("<BBBBBBBBBBIHHH"[: len(attachment) + 1], attachment)

    # Byte 1 Equation byte, use to detect the type of message.
    eq = raw[0]

    # BEAM 10 byte and 20 byte binary messages
    if eq in [1, 2, 3, 4, 18, 19, 25, 26]:
        latitude = int(bin(raw[1])[2:][-3]) * "-"
        latitude_h = str(int("0" + bin(raw[2])[2:][-4:], 2)) + str(int("0" + bin(raw[2])[2:][-8:-4], 2))
        # Byte 3,4 (Latitude HHMM)
        latitude_m = str(int("0" + bin(raw[3])[2:][-4:], 2)) + str(int("0" + bin(raw[3])[2:][-8:-4], 2))
        # Byte 5,6 (Latitude .MMMM)
        latitude_m += "." + str(int("0" + bin(raw[4])[2:][-4:], 2)) + str(int("0" + bin(raw[4])[2:][-8:-4], 2))
        latitude_m += str(int("0" + bin(raw[5])[2:][-4:], 2)) + str(int("0" + bin(raw[5])[2:][-8:-4], 2))

        beam["latitude"] = float(latitude + str(int(latitude_h) + float(latitude_m) / 60))

        longitude = int(bin(raw[1])[2:][-2]) * "-"
        longitude_h = bin(raw[1])[2:][-1]
        # Byte 7,8 (Longitude HHMM)
        longitude_h += str(int("0" + bin(raw[6])[2:][-4:], 2)) + str(int("0" + bin(raw[6])[2:][-8:-4], 2))
        longitude_m = str(int("0" + bin(raw[7])[2:][-4:], 2)) + str(int("0" + bin(raw[7])[2:][-8:-4], 2))
        # Byte 9,10 (Longitude .MMMM)
        longitude_m += "." + str(int("0" + bin(raw[8])[2:][-4:], 2)) + str(int("0" + bin(raw[8])[2:][-8:-4], 2))
        longitude_m += str(int("0" + bin(raw[9])[2:][-4:], 2)) + str(int("0" + bin(raw[9])[2:][-8:-4], 2))
        beam["longitude"] = float(longitude + str(int(longitude_h) + float(longitude_m) / 60))

        if len(raw) == 14:
            # Byte 15,16 are speed in 10 m/h
            beam["velocity"] = raw[11] * 10
            # Byte 17,18 is altitude in m above sea level
            beam["altitude"] = raw[12]
            # Byte 19,20 is direction in degrees
            beam["heading"] = raw[13]
    else:
        return False

    return beam


def parse_iriditrak_message(message: EmailMessage):
    """Parses a passed-in Iriditrak email message. Returns a dict or False."""
    try:
        # Ref: https://docs.python.org/3.11/library/email.utils.html#email.utils.parsedate
        timetuple = parsedate(message["DATE"])
        timestamp = time.mktime(timetuple)  # Timestamp integer.
        # Assume timestamp is UTC, cast timestamp as a datetime object.
        timestamp = datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)

        data = {
            "device_id": message["SUBJECT"].replace("SBD Msg From Unit: ", ""),
            "timestamp": timestamp,
            "type": "iriditrak",
        }

        # BEAM binary message attachment.
        attachment = None
        for part in message.walk():
            if part.get_content_maintype() != "multipart":
                attachment = part.get_payload(decode=True)

        # If the attachment is absent or greater than 20 bytes, abort.
        if not attachment or len(attachment) > 20:
            return False

        beam = parse_beam_payload(attachment)
        if not beam:
            return False

        data = {**data, **beam}

    except:
        return False

    return data


def parse_dplus_payload(payload: str) -> Dict | Literal[False]:
    """DPlus data is received as an email payload consisting of bar-separated values."""
    payload_raw = payload.strip().split("|")
    device_id = payload_raw[0]
    timestamp = payload_raw[1]
    latitude = payload_raw[4]
    longitude = payload_raw[5]
    velocity = payload_raw[6]
    heading = payload_raw[7]
    altitude = payload_raw[9]

    try:
        data = {
            "device_id": int(device_id),
            "timestamp": datetime.strptime(timestamp, "%d-%m-%y %H:%M:%S").replace(tzinfo=timezone.utc),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "velocity": int(velocity) * 1000,
            "heading": int(heading),
            "altitude": int(altitude),
            "type": "dplus",
        }
    except:
        return False

    print(data)
    return data


def parse_tracplus_row(row: Dict) -> Dict | Literal[False]:
    try:
        data = {
            "device_id": row["Device IMEI"],
            "timestamp": datetime.strptime(row["Transmitted"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc),
            "latitude": float(row["Latitude"]),
            "longitude": float(row["Longitude"]),
            "velocity": int(row["Speed"]) * 1000,  # Convert km/h to m/h.
            "heading": int(row["Track"]),
            "altitude": int(row["Altitude"]),
            "type": "tracplus",
        }
    except:
        return False

    return data


def parse_dfes_feature(feature: Dict) -> Dict | Literal[False]:
    """DFES data will be a GeoJSON feature."""
    properties = feature["properties"]
    coordinates = feature["geometry"]["coordinates"]

    try:
        data = {
            "device_id": str(properties["TrackerID"]).strip(),
            "timestamp": datetime.strptime(properties["Time"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc),
            "longitude": coordinates[0],
            "latitude": coordinates[1],
            "velocity": properties["Speed"] * 1000,  # Convert km/h to m/h
            "heading": properties["Direction"],
            "altitude": 0,  # DFES feed does not report altiude.
            "type": "dfes",
            "vehicle_group": properties["VehicleGroupName"].strip(),
        }
    except:
        return False

    return data


def parse_tracertrak_feature(feature: Dict) -> Dict | Literal[False]:
    """TracerTrak data will be GeoJSON features."""
    properties = feature["properties"]
    coordinates = feature["geometry"]["coordinates"]

    try:
        data = {
            "device_id": properties["deviceID"],
            "timestamp": datetime.strptime(properties["logTimestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
            "longitude": coordinates[0],
            "latitude": coordinates[1],
            "velocity": 0,
            "heading": int(properties["heading"]),
            "altitude": 0,
            "type": "spot",
        }
    except:
        return False

    return data


def parse_netstar_feature(feature: Dict) -> Dict | Literal[False]:
    """Features will be a JSON object."""

    try:
        data = {
            "device_id": f"{feature['TrackerID']}",
            "timestamp": datetime.fromisoformat(feature["Time"]).replace(tzinfo=timezone.utc),
            "longitude": feature["Longitude"],
            "latitude": feature["Latitude"],
            "velocity": feature["Speed"] * 1000,  # Convert km/h to m/h
            "heading": feature["Direction"],
            "altitude": 0,  # Feed does not report altiude.
            "type": "netstar",
            "registration": feature["Rego"],
        }
    except:
        return False

    return data


def get_previous_pages(page_obj: Page, count: int = 5) -> List[int]:
    """Convenience function to take a Page object and return the previous `count`
    page numbers, to a minimum of 1.
    """
    prev_page_numbers = []

    if page_obj.has_previous():
        for i in range(page_obj.previous_page_number(), page_obj.previous_page_number() - count, -1):
            if i >= 1:
                prev_page_numbers.append(i)

    prev_page_numbers.reverse()
    return prev_page_numbers


def get_next_pages(page_obj: Page, count: int = 5) -> List[int]:
    """Convenience function to take a Page object and return the next `count`
    page numbers, to a maximum of the paginator page count.
    """
    next_page_numbers = []

    if page_obj.has_next():
        for i in range(page_obj.next_page_number(), page_obj.next_page_number() + count):
            if i <= page_obj.paginator.num_pages:
                next_page_numbers.append(i)

    return next_page_numbers


class SanitizingJSONDecoder(json.JSONDecoder):
    """
    A JSONDecoder that strips ASCII control characters (0–31) from the input
    before parsing, helping to avoid errors when upstream data contains
    non-printable characters.

    Example:
        data = json.loads(raw_json, cls=SanitizingJSONDecoder)
    """

    _ctrl_re = re.compile(r"[\x00-\x1F]")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def _sanitize(cls, s: str) -> str:
        # Replace all ASCII control characters 0–31 with a space.
        # Note: This also removes \n, \r, and \t if present as literal chars.
        return cls._ctrl_re.sub(" ", s)

    def decode(self, s: Any, **kwargs) -> Any:
        # Accept both str and bytes and sanitize prior to decoding.
        if isinstance(s, (bytes, bytearray)):
            s = s.decode("utf-8", errors="replace")
        elif not isinstance(s, str):
            s = str(s)

        s = self._sanitize(s)
        return super().decode(s, **kwargs)
