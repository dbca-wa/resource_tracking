from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add a composite index supporting "newest point per source device type" queries.

    Created CONCURRENTLY so that harvesting is not blocked while the index is built,
    which requires the migration to be non-atomic.
    """

    atomic = False

    dependencies = [
        ("tracking", "0027_alter_device_callsign_display_and_more"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="loggedpoint",
            index=models.Index(fields=["source_device_type", "seen"], name="lp_type_seen_idx"),
        ),
    ]
