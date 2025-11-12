from django.contrib.auth.models import Group, User
from django.test import TestCase


class SignalsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")

    def test_user_in_group(self):
        """Test the created users have the default group set"""
        group = Group.objects.get(name="Edit Resource Tracking Device")
        self.assertTrue(group in self.user.groups.all())
