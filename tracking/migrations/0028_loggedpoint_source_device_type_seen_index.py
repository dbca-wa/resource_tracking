from django.db import migrations, models


class Migration(migrations.Migration):
    """Add a composite index supporting "newest point per source device type" queries.

    This table can be partitioned in PostgreSQL, and CREATE INDEX CONCURRENTLY is not
    valid for a partitioned table. Use the standard index creation path instead.
    """

    dependencies = [
        ("tracking", "0027_alter_device_callsign_display_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="loggedpoint",
            index=models.Index(fields=["source_device_type", "seen"], name="lp_type_seen_idx"),
        ),
    ]
