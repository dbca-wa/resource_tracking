# Generated by Django 2.2.16 on 2021-01-19 00:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0007_auto_20200214_0446'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='source_device_type',
            field=models.CharField(choices=[('tracplus', 'TracPlus'), ('iriditrak', 'Iriditrak'), ('dplus', 'DPlus'), ('spot', 'Spot'), ('dfes', 'DFES'), ('mp70', 'MP70'), ('fleetcare', 'fleetcare'), ('other', 'Other'), ('fleetcare_error', 'Fleetcare (error)')], default='other', max_length=32),
        ),
        migrations.AlterField(
            model_name='loggedpoint',
            name='source_device_type',
            field=models.CharField(choices=[('tracplus', 'TracPlus'), ('iriditrak', 'Iriditrak'), ('dplus', 'DPlus'), ('spot', 'Spot'), ('dfes', 'DFES'), ('mp70', 'MP70'), ('fleetcare', 'fleetcare'), ('other', 'Other'), ('fleetcare_error', 'Fleetcare (error)')], default='other', max_length=32),
        ),
    ]
