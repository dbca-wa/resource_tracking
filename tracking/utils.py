import struct
import time
from datetime import datetime, timezone
from email.utils import parsedate


def validate_latitude_longitude(latitude, longitude):
    """Validate passed-in latitude and longitude values."""
    # Both latitude and longitude equalling zero is considered invalid.
    if latitude == 0.0 and longitude == 0.0:
        return False

    return latitude <= 90 and latitude >= -90 and longitude <= 180 and longitude >= -180


def parse_mp70_payload(payload):
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


def parse_spot_message(message):
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


def parse_beam_payload(attachment):
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


def parse_iriditrak_message(message):
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


def parse_dplus_payload(payload):
    data = {"RAW": payload.strip().split("|")}

    try:
        data["device_id"] = int(data["RAW"][0])
        data["timestamp"] = (datetime.strptime(data["RAW"][1], "%d-%m-%y %H:%M:%S").replace(tzinfo=timezone.utc),)
        data["latitude"] = float(data["RAW"][4])
        data["longitude"] = float(data["RAW"][5])
        data["velocity"] = int(data["RAW"][6]) * 1000
        data["heading"] = int(data["RAW"][7])
        data["altitude"] = int(data["RAW"][9])
        data["type"] = "dplus"
    except:
        return False

    return data


def parse_tracplus_row(row):
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

    return data


def parse_dfes_feature(feature):
    """Features will be GeoJSON"""
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
        }
    except:
        return False

    return data


def parse_tracertrak_feature(feature):
    """Features will be GeoJSON"""
    properties = feature["properties"]
    coordinates = feature["geometry"]["coordinates"]

    try:
        data = {
            "device_id": properties["deviceID"],
            "timestamp": datetime.strptime(properties["logTimestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            ),
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
