# Generated by Django 2.1.11 on 2020-01-02 01:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0003_auto_20190308_1114'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='symbol',
            field=models.CharField(choices=[('2 wheel drive', '2-Wheel Drive'), ('4 wheel drive passenger', '4-Wheel Drive Passenger'), ('4 wheel drive ute', '4-Wheel Drive (Ute)'), ('light unit', 'Light Unit'), ('heavy duty', 'Heavy Duty'), ('gang truck', 'Gang Truck'), ('snorkel', 'Snorkel'), ('dozer', 'Dozer'), ('grader', 'Grader'), ('loader', 'Loader'), ('tender', 'Tender'), ('float', 'Float'), ('fixed wing aircraft', 'Waterbomber'), ('rotary aircraft', 'Rotary'), ('spotter aircraft', 'Spotter'), ('helitac', 'Helitac'), ('rescue helicopter', 'Rescue Helicopter'), ('aviation fuel truck', 'Aviation Fuel Truck'), (None, ''), ('comms bus', 'Communications Bus'), ('boat', 'Boat'), ('person', 'Person'), ('other', 'Other'), ('unknown', 'Unknown')], default='other', max_length=32),
        ),
    ]
