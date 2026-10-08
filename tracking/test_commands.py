from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from tracking.models import Device, LoggedPoint


class DummyDataCommandTestCase(TestCase):
    @override_settings(DEBUG=True)
    def test_tracking_generate_dummy_data_creates_realistic_records(self):
        call_command("tracking_generate_dummy_data", devices=3, logged_points=8)

        self.assertEqual(Device.objects.count(), 3)
        self.assertEqual(LoggedPoint.objects.count(), 8)

        for device in Device.objects.all():
            self.assertIsNotNone(device.point)
            self.assertGreater(device.point.x, 115.5)
            self.assertLess(device.point.x, 116.3)
            self.assertGreater(device.point.y, -32.3)
            self.assertLess(device.point.y, -31.5)
            self.assertIn(device.symbol, [choice[0] for choice in Device._meta.get_field("symbol").choices if choice[0]])
            self.assertIn(device.source_device_type, [choice[0] for choice in Device._meta.get_field("source_device_type").choices])

        for logged_point in LoggedPoint.objects.all():
            self.assertIsNotNone(logged_point.point)
            self.assertGreater(logged_point.point.x, 115.5)
            self.assertLess(logged_point.point.x, 116.3)
            self.assertGreater(logged_point.point.y, -32.3)
            self.assertLess(logged_point.point.y, -31.5)
            self.assertIn(
                logged_point.source_device_type, [choice[0] for choice in LoggedPoint._meta.get_field("source_device_type").choices]
            )

    @override_settings(DEBUG=False)
    def test_tracking_generate_dummy_data_requires_debug_mode(self):
        with self.assertRaises(CommandError):
            call_command("tracking_generate_dummy_data", devices=1, logged_points=1)
