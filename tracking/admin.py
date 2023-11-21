from django.conf import settings
from django.contrib.admin import ModelAdmin, register, AdminSite
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Device


@register(Device)
class DeviceAdmin(ModelAdmin):
    actions = None
    date_hierarchy = "seen"
    list_display = (
        "id", "deviceid", "source_device_type", "registration", "callsign", "rin_display", "symbol", "district_display",
        "seen", "hidden", "internal_only",
    )
    list_filter = ("symbol", "district", "source_device_type", "hidden", "internal_only")
    search_fields = ("deviceid", "registration", "callsign_display", "rin_display", "symbol", "district_display")
    readonly_fields = ("deviceid", "source_device_type", "seen", "point")
    fieldsets = (
        ("Vehicle/Device details", {
            "description": """<p class="errornote">This is the live tracking database;
            changes made to these fields will apply to the Device Tracking map in all
            variants of the Spatial Support System.</p>
            """ if settings.PROD_SCARY_WARNING else "",
            "fields": (
                "deviceid",
                "source_device_type",
                "seen",
                "point",
                "district",
                "symbol",
                "callsign",
                "registration",
                "rin_number",
                "fire_use",
            ),
        }),
        ("Crew Details", {
            "fields": ("current_driver", "usual_driver", "usual_location")
        }),
        ("Contractor Details", {
            "fields": ("contractor_details",)
        }),
        ("Other Details", {
            "fields": ("other_details", "internal_only", "hidden")
        })
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.source_device_type == 'tracplus':
            return False
        else:
            return super(DeviceAdmin, self).has_change_permission(request, obj=obj)


class DeviceSSSAdmin(DeviceAdmin):

    def add_view(self, request, obj=None):
        return HttpResponseRedirect(reverse('sss_admin:tracking_device_changelist'))


class TrackingAdminSite(AdminSite):
    site_header = 'SSS administration'
    site_url = None


tracking_admin_site = TrackingAdminSite(name='sss_admin')
tracking_admin_site.register(Device, DeviceSSSAdmin)
