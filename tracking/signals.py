from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # Set is_staff to True so users can edit Device details
    instance.is_staff = True


@receiver(post_save, sender=User)
def user_post_save(sender, instance, **kwargs):
    # Add users to the 'Edit Resource Tracking Device' group so users can edit Device details
    # NOTE: does not work when saving user in Django Admin
    g, created = Group.objects.get_or_create(name="Edit Resource Tracking Device")
    instance.groups.add(g)
