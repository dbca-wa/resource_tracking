from django.apps import AppConfig


class TrackingConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "tracking"

    def ready(self):
        # Import module signals.
        from tracking import signals
