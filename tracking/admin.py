from django.conf import settings
from django.contrib.admin import ModelAdmin, register, AdminSite
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from .models import Device, LoggedPoint


@register(Device)
class DeviceAdmin(ModelAdmin):
    date_hierarchy = "seen"
    list_display = ("deviceid", "name", "callsign", "symbol", "district", "seen")
    list_filter = ("symbol", "district")
    search_fields = ("deviceid", "name", "callsign", "symbol", "district")
    readonly_fields = ("deviceid",)
    fields = ("deviceid", "symbol", "district", "callsign", "name")

    class Media:
        js = (
            settings.JQUERY_SOURCE,
            settings.JQUERYUI_SOURCE,
        )

@register(LoggedPoint)
class LoggedPointAdmin(ModelAdmin):
    list_display = ("seen", "device")
    list_filter = ("device__symbol", "device__district")
    search_fields = ("device__deviceid", "device__name", "device__callsign")
    date_hierarchy = "seen"

    def change_view(self, request, obj=None):
        return HttpResponseRedirect(reverse('admin:tracking_loggedpoint_changelist'))


class TrackingAdminSite(AdminSite):
    site_header = 'SSS administration'
    site_url = None

tracking_admin_site = TrackingAdminSite(name='tracking_admin')
tracking_admin_site.register(Device, DeviceAdmin)

