# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=128, blank=True)),
                ('description', models.TextField(blank=True)),
                ('point', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('height', models.DecimalField(max_digits=7, decimal_places=3)),
            ],
        ),
        migrations.CreateModel(
            name='WeatherObservation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('raw_data', models.TextField()),
                ('temperature_min', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('temperature_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('temperature', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('temperature_deviation', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('temperature_outliers', models.PositiveIntegerField(null=True, blank=True)),
                ('pressure_min', models.DecimalField(null=True, max_digits=5, decimal_places=1, blank=True)),
                ('pressure_max', models.DecimalField(null=True, max_digits=5, decimal_places=1, blank=True)),
                ('pressure', models.DecimalField(null=True, max_digits=5, decimal_places=1, blank=True)),
                ('pressure_deviation', models.DecimalField(null=True, max_digits=5, decimal_places=1, blank=True)),
                ('pressure_outliers', models.PositiveIntegerField(null=True, blank=True)),
                ('humidity_min', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('humidity_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('humidity', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('humidity_deviation', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('humidity_outliers', models.PositiveIntegerField(null=True, blank=True)),
                ('wind_direction_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_direction_min', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_direction', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_direction_deviation', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_direction_outliers', models.PositiveIntegerField(null=True, blank=True)),
                ('wind_speed_max', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed_min', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed_deviation', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed_outliers', models.PositiveIntegerField(null=True, blank=True)),
                ('wind_speed_max_kn', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed_min_kn', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed_kn', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('wind_speed_deviation_kn', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('rainfall', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('actual_rainfall', models.DecimalField(null=True, max_digits=4, decimal_places=1, blank=True)),
                ('actual_pressure', models.DecimalField(null=True, max_digits=5, decimal_places=1, blank=True)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='WeatherStation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbreviation', models.CharField(max_length=20)),
                ('bom_abbreviation', models.CharField(max_length=4)),
                ('ip_address', models.GenericIPAddressField()),
                ('port', models.PositiveIntegerField(default=43000)),
                ('last_scheduled', models.DateTimeField()),
                ('last_reading', models.DateTimeField()),
                ('battery_voltage', models.DecimalField(max_digits=3, decimal_places=1)),
                ('connect_every', models.PositiveSmallIntegerField(default=15)),
                ('active', models.BooleanField(default=False)),
                ('stay_connected', models.BooleanField(default=False, verbose_name='Persistant connection')),
                ('location', models.ForeignKey(blank=True, to='weather.Location', null=True)),
            ],
            options={
                'ordering': ['-last_reading'],
            },
        ),
        migrations.AddField(
            model_name='weatherobservation',
            name='station',
            field=models.ForeignKey(related_name='readings', to='weather.WeatherStation'),
        ),
        migrations.AlterUniqueTogether(
            name='weatherobservation',
            unique_together=set([('station', 'date')]),
        ),
    ]
