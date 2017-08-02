from __future__ import unicode_literals

from django.db import migrations
from tracking.models import Device

def usual_callsign_to_current_callsign(apps, schema_editor):
    try:
        for d in Device.objects.exclude(usual_callsign=None).exclude(usual_callsign=''):
            d.current_callsign = d.usual_callsign
            d.save()
    except: pass
    
class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0026_auto_20170616_1253'),
    ]

    operations = [
        migrations.RunPython(usual_callsign_to_current_callsign),
    ]
