# Generated by Django 2.1.11 on 2020-02-13 20:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0006_auto_20200213_1716'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='hidden',
            field=models.BooleanField(default=False, verbose_name='Hidden/private use'),
        ),
    ]
