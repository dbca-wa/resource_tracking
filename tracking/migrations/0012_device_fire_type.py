# Generated by Django 3.2.5 on 2021-10-17 21:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0011_auto_20210423_0941'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='fire_type',
            field=models.NullBooleanField(default=None, verbose_name='Fire type'),
        ),
    ]
