from __future__ import unicode_literals

from django.db import migrations
from tracking.models import Device

def copy_callsign_name_to_other_details(apps, schema_editor):
    try:
        for d in Device.objects.all():
			d.other_details = d.callsign + '\r\n' + d.name
			d.save()
    except: pass

class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0016_auto_20170131_1448'),
    ]

    operations = [
        migrations.RunPython(copy_callsign_name_to_other_details),
    ]

