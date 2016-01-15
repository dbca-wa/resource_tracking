# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('point', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True, editable=False)),
                ('heading', models.PositiveIntegerField(default=0, help_text='Heading in degrees', editable=False)),
                ('velocity', models.PositiveIntegerField(default=0, help_text='Speed in metres/hr', editable=False)),
                ('altitude', models.IntegerField(default=0, help_text='Altitude above sea level in metres', editable=False)),
                ('seen', models.DateTimeField(null=True, editable=False)),
                ('deviceid', models.CharField(unique=True, max_length=32)),
                ('name', models.CharField(default='No Name', max_length=32)),
                ('callsign', models.CharField(default='No Callsign', max_length=32)),
                ('symbol', models.CharField(default='Other', max_length=32)),
                ('rego', models.CharField(max_length=10, null=True, blank=True)),
                ('make', models.CharField(max_length=55, null=True, blank=True)),
                ('model', models.CharField(max_length=55, null=True, blank=True)),
                ('category', models.CharField(max_length=55, null=True, blank=True)),
            ],
            options={
                'ordering': ['-seen'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LoggedPoint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('point', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True, editable=False)),
                ('heading', models.PositiveIntegerField(default=0, help_text='Heading in degrees', editable=False)),
                ('velocity', models.PositiveIntegerField(default=0, help_text='Speed in metres/hr', editable=False)),
                ('altitude', models.IntegerField(default=0, help_text='Altitude above sea level in metres', editable=False)),
                ('seen', models.DateTimeField(null=True, editable=False)),
                ('raw', models.TextField(editable=False)),
                ('device', models.ForeignKey(editable=False, to='tracking.Device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='loggedpoint',
            unique_together=set([('device', 'seen')]),
        ),
    ]
