import csv
import email
import os
from datetime import datetime, timezone

import orjson as json
from django.conf import settings
from django.test import TestCase

from tracking.models import Device
from tracking.utils import (
    parse_beam_payload,
    parse_dfes_feature,
    parse_iriditrak_message,
    parse_mp70_payload,
    parse_netstar_feature,
    parse_tracplus_row,
    validate_latitude_longitude,
)

# MP70 payload with valid data.
MP70_PAYLOAD_VALID = "\r\nN694470090021038,13.74,-031.99252,+115.88450,0,0,10/18/2023 03:12:45\r\n"
MP70_TIMESTAMP = datetime(2023, 10, 18, 3, 12, 45, tzinfo=timezone.utc)
# MP70 payload with bad data (unable to parse).
MP70_PAYLOAD_BAD = "\r\nN690540113021035,12.96,foo,bar,-53,0,10/18/2023 03:12:49\r\n"
# MP70 payload with invalid data (fails validation).
MP70_PAYLOAD_INVALID = "\r\nN690540113021035,12.96,+000.00000,+000.00000,-53,0,10/18/2023 03:12:49\r\n"
# Iriditrak BEAM payload with valid data.
IRIDITRAK_PAYLOAD_VALID = b"\x03\xadCSB\x00aa\x80\x11,U\xeee]\x1b\x97\x00J\x01"
# Iriditrak timestamp in the test email message.
IRIDTRAK_TIMESTAMP = datetime(2024, 3, 11, 0, 50, 1, tzinfo=timezone.utc)
# TracPlus feed valid payload
TRAKPLUS_FEED_VALID = """Report ID,Asset Type,Asset Regn,Asset Name,Asset Make,Asset Model,Device ID,Device Serial,Device IMEI,Device Make,Device Model,Transmitted,Received,Latitude,Longitude,Speed,Track,Altitude,Events,GPS Count,DOP,Type of Fix,Message Text,Package,Gateway\r\n1,Aircraft,N293EA Erickson Aero Tanker,,McDonnell Douglas,DC-87,1,L0001,L1001,Flightcell,DZMx,2023-10-30 01:50:44,2023-10-30 01:50:49,44.66921790,-121.149994450,0,0,750,EVT_SCHEDULED,0,1,3D,,,IRIDIUM.SBD.SQS
"""
TRAKPLUS_TIMESTAMP = datetime(2023, 10, 30, 1, 50, 44, tzinfo=timezone.utc)
DFES_FEED_FEATURE_VALID = """{
    "type": "Feature",
    "id": "VehPos.3",
    "geometry": {
        "type": "Point",
        "coordinates": [
            116.694476666667,
            -31.9609566666667
        ]
    },
    "geometry_name": "the_geom",
    "properties": {
        "TrackerID": 1001,
        "VehicleName": "Talbot Brook BFB 2.4B",
        "VehicleID": "E430",
        "Driver": "",
        "VehicleGroupName": "Goldfield Mland BFB",
        "VehicleDepartmentName": "Goldfields Midlands",
        "VehicleGroupCode": "G0_BFB",
        "VehicleDepartmentCode": "G0",
        "Registration": "1CMQ210",
        "VehicleType": "2.4 BROADACRE",
        "Model": "FSS550",
        "Manufacturer": "ISUZU",
        "UniqueCode": "U103287",
        "Time": "2023-10-05T01:40:07.0Z",
        "Speed": 0,
        "Direction": 228,
        "Emergency": false,
        "RolloverAlarm": false
    }
}"""
DFES_TIMESTAMP = datetime(2023, 10, 5, 1, 40, 7, tzinfo=timezone.utc)
NETSTAR_FEED_FEATURE_VALID = """
{
      "TrackerID": 101,
      "VehicleName": "752TIP19A",
      "Time": "2025-04-09T03:47:54",
      "Latitude": -31.965133333333331,
      "Longitude": 115.98455833333334,
      "GpsLocked": false,
      "Speed": 0.0,
      "Direction": 319.0,
      "Ignition": false,
      "OdometerInMetres": 90200,
      "EngineHoursInSeconds": 404725,
      "SuburbOrZone": "FORRESTFIELD",
      "VehicleIdExternal": "F257831",
      "Rego": "752TIP19A",
      "Model": "NPS",
      "Manufacturer": "ISUZU",
      "EmergencyDistressAlarm": false,
      "RolloverAlert": false,
      "OnSat": false
}"""
NETSTAR_TIMESTAMP = datetime(2025, 4, 9, 3, 47, 54, tzinfo=timezone.utc)


class HarvestTestCase(TestCase):
    """Unit tests to cover the following harvest formats:
    - Email payloads: Iriditrak, MP70
    - TracPlus API
    - DFES API

    TODO: Email from Spot, DPlus
    """

    def test_validate_latitude_longitude(self):
        """Test the validate_latitude_longitude function"""
        data = parse_mp70_payload(MP70_PAYLOAD_INVALID)
        self.assertFalse(validate_latitude_longitude(data["latitude"], data["longitude"]))
        data = parse_mp70_payload(MP70_PAYLOAD_VALID)
        self.assertTrue(validate_latitude_longitude(data["latitude"], data["longitude"]))

    def test_parse_mp70_payload(self):
        """Test the parse_mp70_payload function"""
        data = parse_mp70_payload(MP70_PAYLOAD_VALID)
        self.assertTrue(data)
        self.assertEqual(data["timestamp"], MP70_TIMESTAMP)
        # Invalid data will still parse.
        self.assertTrue(parse_mp70_payload(MP70_PAYLOAD_INVALID))
        self.assertFalse(parse_mp70_payload(MP70_PAYLOAD_BAD))

    def test_parse_beam_payload(self):
        """Test the parse_beam_payload function"""
        self.assertTrue(parse_beam_payload(IRIDITRAK_PAYLOAD_VALID))

    def test_parse_iriditrak_message(self):
        # Iriditrak timestamp is parsed from the sent email.
        iriditrak_email = open(os.path.join(settings.BASE_DIR, "tracking", "iriditrak_test.msg"))
        message = email.message_from_string(iriditrak_email.read())
        data = parse_iriditrak_message(message)
        self.assertEqual(IRIDTRAK_TIMESTAMP, data["timestamp"])

    def test_parse_spot_message(self):
        """TODO: test the parse_spot_message function"""
        pass

    def test_parse_tracplus_row(self):
        """Test the parse_tracplus_row function"""
        self.assertFalse(Device.objects.filter(source_device_type="tracplus").exists())
        csv_data = csv.DictReader(TRAKPLUS_FEED_VALID.split("\r\n"))
        row = next(csv_data)
        data = parse_tracplus_row(row)
        self.assertTrue(data)
        self.assertEqual(data["timestamp"], TRAKPLUS_TIMESTAMP)

    def test_parse_dfes_feature(self):
        """Test the parse_dfes_feature function"""
        feature = json.loads(DFES_FEED_FEATURE_VALID)
        data = parse_dfes_feature(feature)
        self.assertTrue(data)
        self.assertEqual(data["timestamp"], DFES_TIMESTAMP)

    def test_parse_netstar_feature(self):
        feature = json.loads(NETSTAR_FEED_FEATURE_VALID)
        data = parse_netstar_feature(feature)
        self.assertTrue(data)
        self.assertEqual(data["timestamp"], NETSTAR_TIMESTAMP)
