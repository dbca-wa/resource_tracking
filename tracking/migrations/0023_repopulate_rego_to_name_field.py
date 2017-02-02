from __future__ import unicode_literals

from django.db import migrations
from tracking.models import Device

def copy_rego_to_name(apps, schema_editor):
	for d in Device.objects.all():
		try:
			if d.other_details.split('\r\n')[1] != '':
				d.name = d.other_details.split('\r\n')[1]
				d.save()
			elif d.other_details.split('\r\n')[0] != '':
				d.name = d.other_details.split('\r\n')[0]
				d.save()
		except:
			try:
				d.name = d.other_details
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

