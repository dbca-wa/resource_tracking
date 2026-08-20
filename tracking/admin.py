from django.contrib.admin import ModelAdmin, register

from .models import Device


@register(Device)
class DeviceAdmin(ModelAdmin):
    actions = None
    date_hierarchy = "seen"
    list_display = (
        "id",
        "deviceid",
        "source_device_type",
        "registration",
        "callsign",
        "rin_display",
        "symbol",
        "district_display",
        "seen",
        "hidden",
        "internal_only",
    )
    list_filter = ("symbol", "district", "source_device_type", "hidden", "internal_only")
    search_fields = ("deviceid", "registration", "callsign", "rin_display", "symbol", "district_display")
    readonly_fields = ("deviceid", "source_device_type", "seen", "point", "registration")
    fieldsets = (
        (
            "Vehicle/Device details",
            {
                "fields": (
                    "deviceid",
                    "source_device_type",
                    "registration",
                    "seen",
                    "district",
                    "symbol",
                    "callsign",
                    "rin_number",
                    "fire_use",
                ),
            },
        ),
        ("Crew Details", {"fields": ("current_driver", "usual_driver", "usual_location")}),
        ("Contractor Details", {"fields": ("contractor_details",)}),
        ("Other Details", {"fields": ("other_details", "internal_only", "hidden")}),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # TracPlus and DFES vehicles have an external source of truth regarding metadata.
        if obj is not None and obj.source_device_type in ["tracplus", "dfes"]:
            return False
        else:
            return super().has_change_permission(request, obj=obj)
