from __future__ import unicode_literals

from django.db import migrations
from tracking.models import Device

def create_tracking_resource_tracking_ext_view(apps, schema_editor):
	from django.db import connection
	cursor = connection.cursor()
	cursor.execute('''
    CREATE OR REPLACE VIEW tracking_resource_tracking_ext_view AS
		SELECT resource_tracking_with_age.id,
        resource_tracking_with_age.point,
        resource_tracking_with_age.heading,
        resource_tracking_with_age.velocity,
        resource_tracking_with_age.altitude,
        resource_tracking_with_age.seen,
        resource_tracking_with_age.deviceid,
        resource_tracking_with_age.registration,
        resource_tracking_with_age.rin_display,
        resource_tracking_with_age.current_driver,
        resource_tracking_with_age.callsign,
        resource_tracking_with_age.callsign_display,
        resource_tracking_with_age.usual_driver,
        resource_tracking_with_age.usual_location,
        resource_tracking_with_age.contractor_details,
        resource_tracking_with_age.symbol,
        resource_tracking_with_age.age,
        replace(lower((resource_tracking_with_age.symbol)::text), ' '::text, '_'::text) AS symbolid,
        resource_tracking_with_age.district,
        resource_tracking_with_age.district_display,
        resource_tracking_with_age.source_device_type
       FROM ( SELECT tracking_device.id,
                tracking_device.point,
                tracking_device.heading,
                tracking_device.velocity,
                tracking_device.altitude,
                tracking_device.seen,
                tracking_device.deviceid,
                tracking_device.registration,
                tracking_device.rin_display,
                tracking_device.current_driver,
                tracking_device.callsign,
                tracking_device.callsign_display,
                tracking_device.usual_driver,
                tracking_device.usual_location,
                tracking_device.contractor_details,
                tracking_device.symbol,
                (((date_part('day'::text, (now() - tracking_device.seen)) * (24)::double precision) + date_part('hour'::text, (now() - tracking_device.seen))) + (1)::double precision) AS age,
                tracking_device.district,
                tracking_device.district_display,
                tracking_device.source_device_type,
                tracking_device.internal_only
               FROM tracking_device) resource_tracking_with_age
      WHERE (resource_tracking_with_age.age < (168)::double precision)
		AND resource_tracking_with_age.internal_only = False;''')

class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0031_device_internal_only'),
    ]

    operations = [
        migrations.RunPython(create_tracking_resource_tracking_ext_view),
    ]
