from __future__ import unicode_literals

from django.db import migrations
from tracking.models import Device

def cleanup_callsign(apps, schema_editor):
    try:
        for d in Device.objects.filter(callsign=''):
            d.callsign = None
            d.save()
    except: pass
    
def update_district_display(apps, schema_editor):
    try:
        for d in Device.objects.all():
            d.district_display = d.get_district_display()
            d.save()
    except: pass
    
class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0030_device_district_display'),
    ]

    operations = [
        migrations.RunPython(cleanup_callsign),
        migrations.RunPython(update_district_display),
    ]
