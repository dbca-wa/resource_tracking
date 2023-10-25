from django.test import TestCase
from tracking.utils import (
    validate_latitude_longitude,
    parse_mp70_payload,
    parse_beam_payload,
)


# MP70 payload with valid data.
MP70_PAYLOAD_VALID = "\r\nN694470090021038,13.74,-031.99252,+115.88450,0,0,10/18/2023 03:12:45\r\n"
# MP70 payload with bad data (unable to parse).
MP70_PAYLOAD_BAD = "\r\nN690540113021035,12.96,foo,bar,-53,0,10/18/2023 03:12:49\r\n"
# MP70 payload with invalid data (fails validation).
MP70_PAYLOAD_INVALID = "\r\nN690540113021035,12.96,+000.00000,+000.00000,-53,0,10/18/2023 03:12:49\r\n"
# Iriditrak payload with valid data.
IRIDITRAK_PAYLOAD_VALID = b"\x01\xfd3\x12tqa\x901 \x11\xd60e\x00\x00\xbc\x00\x00\x00"


class HarvestTestCase(TestCase):
    """Unit tests to cover the following harvest formats:
    - Email payloads: Iriditrak, MP70, Spot
    - DFES API (TODO)
    - TracPlus API (TODO)
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
