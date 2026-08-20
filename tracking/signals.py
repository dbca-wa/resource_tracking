from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    # Add users to the 'Edit Resource Tracking Device' group so users can edit Device details
    # All users have this change permission by default.
    # Reference: https://dbca.freshservice.com/a/tickets/223528
    if created:
        g, _ = Group.objects.get_or_create(name="Edit Resource Tracking Device")
        instance.groups.add(g)
