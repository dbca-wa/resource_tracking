# Generated by Django 2.1.11 on 2020-02-13 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0005_device_hidden'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='hidden',
            field=models.BooleanField(default=True, verbose_name='Hidden/private use'),
        ),
        migrations.AlterField(
            model_name='device',
            name='source_device_type',
            field=models.CharField(choices=[('tracplus', 'TracPlus'), ('iriditrak', 'Iriditrak'), ('dplus', 'DPlus'), ('spot', 'Spot'), ('dfes', 'DFES'), ('mp70', 'MP70'), ('fleetcare', 'fleetcare'), ('other', 'Other')], default='other', max_length=32),
        ),
        migrations.AlterField(
            model_name='loggedpoint',
            name='source_device_type',
            field=models.CharField(choices=[('tracplus', 'TracPlus'), ('iriditrak', 'Iriditrak'), ('dplus', 'DPlus'), ('spot', 'Spot'), ('dfes', 'DFES'), ('mp70', 'MP70'), ('fleetcare', 'fleetcare'), ('other', 'Other')], default='other', max_length=32),
        ),
    ]
