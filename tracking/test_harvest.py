import csv
import json
from django.test import TestCase

from tracking.models import Device
from tracking.utils import (
    validate_latitude_longitude,
    parse_mp70_payload,
    parse_beam_payload,
    parse_tracplus_row,
    parse_dfes_feature,
)


# MP70 payload with valid data.
MP70_PAYLOAD_VALID = "\r\nN694470090021038,13.74,-031.99252,+115.88450,0,0,10/18/2023 03:12:45\r\n"
# MP70 payload with bad data (unable to parse).
MP70_PAYLOAD_BAD = "\r\nN690540113021035,12.96,foo,bar,-53,0,10/18/2023 03:12:49\r\n"
# MP70 payload with invalid data (fails validation).
MP70_PAYLOAD_INVALID = "\r\nN690540113021035,12.96,+000.00000,+000.00000,-53,0,10/18/2023 03:12:49\r\n"
# Iriditrak BEAM payload with valid data.
IRIDITRAK_PAYLOAD_VALID = b"\x01\xfd3\x12tqa\x901 \x11\xd60e\x00\x00\xbc\x00\x00\x00"
# TracPlus feed valid payload
TRAKPLUS_FEED_VALID = """Report ID,Asset Type,Asset Regn,Asset Name,Asset Make,Asset Model,Device ID,Device Serial,Device IMEI,Device Make,Device Model,Transmitted,Received,Latitude,Longitude,Speed,Track,Altitude,Events,GPS Count,DOP,Type of Fix,Message Text,Package,Gateway\r\n1,Aircraft,N293EA Erickson Aero Tanker,,McDonnell Douglas,DC-87,1,L0001,L1001,Flightcell,DZMx,2023-10-30 01:50:44,2023-10-30 01:50:49,44.66921790,-121.149994450,0,0,750,EVT_SCHEDULED,0,1,3D,,,IRIDIUM.SBD.SQS
"""
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


class HarvestTestCase(TestCase):
    """Unit tests to cover the following harvest formats:
    - Email payloads: Iriditrak, MP70, Spot (TODO)
    - TracPlus API
    - DFES API (TODO)
    """

    def test_validate_latitude_longitude(self):
        """Test the validate_latitude_longitude function
        """
        data = parse_mp70_payload(MP70_PAYLOAD_INVALID)
        self.assertFalse(validate_latitude_longitude(data["latitude"], data["longitude"]))
        data = parse_mp70_payload(MP70_PAYLOAD_VALID)
        self.assertTrue(validate_latitude_longitude(data["latitude"], data["longitude"]))

    def test_parse_mp70_payload(self):
        """Test the parse_mp70_payload function
        """
        self.assertTrue(parse_mp70_payload(MP70_PAYLOAD_VALID))
        # Invalid data will still parse.
        self.assertTrue(parse_mp70_payload(MP70_PAYLOAD_INVALID))
        self.assertFalse(parse_mp70_payload(MP70_PAYLOAD_BAD))

    def test_parse_beam_payload(self):
        """Test the parse_beam_payload function
        """
        self.assertTrue(parse_beam_payload(IRIDITRAK_PAYLOAD_VALID))

    def test_parse_spot_message(self):
        """TODO: test the parse_spot_message function
        """
        pass

    def test_parse_tracplus_row(self):
        """Test the parse_tracplus_row function
        """
        self.assertFalse(Device.objects.filter(source_device_type="tracplus").exists())
        csv_data = csv.DictReader(TRAKPLUS_FEED_VALID.split("\r\n"))
        row = next(csv_data)
        self.assertTrue(parse_tracplus_row(row))

    def test_parse_dfes_feature(self):
        """Test the parse_dfes_feature function
        """
        feature = json.loads(DFES_FEED_FEATURE_VALID)
        self.assertTrue(parse_dfes_feature(feature))
