from django.contrib.gis import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from .models import Device, LoggedPoint


class DeviceAdmin(admin.ModelAdmin):
    date_hierarchy = "seen"
    list_display = ("deviceid", "name", "callsign", "symbol", "rego", "make", "model", "category", "seen")
    list_filter = ("symbol", "make", "model", "category")
    search_fields = ("deviceid", "name", "callsign", "symbol", "rego", "make", "model", "category")


class LoggedPointAdmin(admin.ModelAdmin):
    list_display = ("seen", "device")
    list_filter = ("device__symbol", "device__make", "device__model", "device__category")
    search_fields = ("device__deviceid", "device__name", "device__callsign", "device__rego")
    date_hierarchy = "seen"

    def change_view(self, request, obj=None):
        return HttpResponseRedirect(reverse('admin:tracking_loggedpoint_changelist'))

site = admin.AdminSite()

site.register(Device, DeviceAdmin)
site.register(LoggedPoint, LoggedPointAdmin)
