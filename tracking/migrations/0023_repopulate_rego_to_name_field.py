from __future__ import unicode_literals

from django.db import migrations
from tracking.models import Device

def copy_rego_to_name(apps, schema_editor):
    for d in Device.objects.all():
        try:
            callsign = d.other_details.split('\r\n')[0]
            name = d.other_details.split('\r\n')[1]
            if name != '':
                d.name = name
                d.other_details = callsign
                d.save()
            elif callsign != '':
                d.name = callsign
                d.other_details = None
                d.save()
        except:
            try:
                d.name = d.other_details
                d.other_details = None
                d.save()
            except: pass
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0023_auto_20170202_1502'),
    ]

    operations = [
        migrations.RunPython(copy_rego_to_name),
    ]

