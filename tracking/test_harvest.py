import csv
import os
from datetime import datetime, timezone
from email import message_from_file
from email.message import EmailMessage
from email.policy import default

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
    parse_spot_message,
    parse_tracplus_row,
    parse_zoleo_message,
    validate_latitude_longitude,
)

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
    - Email payloads: Iriditrak, MP70, Spot
    - TracPlus API
    - DFES API
    """

    def setUp(self):
        self.test_data_path = os.path.join(settings.BASE_DIR, "tracking", "test_data")

    def test_validate_latitude_longitude(self):
        """Test the validate_latitude_longitude function"""
        mp70_payload_valid = "\r\nN694470090021038,13.74,-031.99252,+115.88450,0,0,10/18/2023 03:12:45\r\n"
        data = parse_mp70_payload(mp70_payload_valid)
        self.assertTrue(validate_latitude_longitude(data["latitude"], data["longitude"]))
        mp70_payload_invalid = "\r\nN690540113021035,12.96,+000.00000,+000.00000,-53,0,10/18/2023 03:12:49\r\n"
        data = parse_mp70_payload(mp70_payload_invalid)
        self.assertFalse(validate_latitude_longitude(data["latitude"], data["longitude"]))

    def test_parse_mp70_payload(self):
        """Test the parse_mp70_payload function"""
        with open(os.path.join(self.test_data_path, "mp70_test.eml")) as f:
            message = message_from_file(f)
        # payload = message.get_payload()
        payload_bytes = message.get_payload(decode=True)
        charset = message.get_content_charset() or "utf-8"
        payload = payload_bytes.decode(charset, errors="replace")
        data = parse_mp70_payload(payload)
        self.assertTrue(data)
        # Correct data in the test email message.
        self.assertEqual(data["device_id"], "TestMP70")
        self.assertEqual(data["timestamp"], datetime(2025, 11, 4, 1, 56, 58, tzinfo=timezone.utc))

    def test_parse_beam_payload(self):
        """Test the parse_beam_payload function"""
        with open(os.path.join(self.test_data_path, "beam_payload_test.sbd"), "rb") as f:
            beam_payload = f.read()
        data = parse_beam_payload(beam_payload)
        self.assertTrue(data)
        self.assertTrue(data["latitude"])
        self.assertTrue(data["longitude"])

    def test_parse_iriditrak_message(self):
        # Iriditrak timestamp is parsed from the sent email.
        with open(os.path.join(self.test_data_path, "iriditrak_test.eml")) as f:
            message = message_from_file(f)
        data = parse_iriditrak_message(message)
        self.assertTrue(data)
        # Correct data in the test email message.
        self.assertEqual(data["device_id"], "TestIriditrak")
        self.assertEqual(data["timestamp"], datetime(2025, 11, 4, 1, 2, 57, tzinfo=timezone.utc))

    def test_parse_spot_message(self):
        """Test the parse_spot_message function"""
        with open(os.path.join(self.test_data_path, "spot_test.eml")) as f:
            message = message_from_file(f)
        data = parse_spot_message(message)
        self.assertTrue(data)
        # Correct data in the test email message.
        self.assertEqual(data["device_id"], "TestSpot")
        self.assertEqual(data["timestamp"], datetime(2025, 11, 4, 0, 38, 54, tzinfo=timezone.utc))

    def test_parse_zoleo_message(self):
        """Test the parse_zoleo_message function"""
        with open(os.path.join(self.test_data_path, "zoleo_test.eml")) as f:
            message = message_from_file(f, _class=EmailMessage, policy=default)
        data = parse_zoleo_message(message)
        self.assertTrue(data)
        # Correct data in the test email message.
        self.assertEqual(data["device_id"], "GLD - Zoleo 9")
        self.assertEqual(data["timestamp"], datetime(2025, 12, 10, 4, 54, 2, tzinfo=timezone.utc))

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
