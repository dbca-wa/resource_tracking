from django.contrib.admin import ModelAdmin, register
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from .models import Device, LoggedPoint


@register(Device)
class DeviceAdmin(ModelAdmin):
    date_hierarchy = "seen"
    list_display = ("deviceid", "name", "callsign", "symbol", "district", "rego", "make", "model", "category", "seen")
    list_filter = ("symbol", "district", "make", "model", "category")
    search_fields = ("deviceid", "name", "callsign", "symbol", "district", "rego", "make", "model", "category")


@register(LoggedPoint)
class LoggedPointAdmin(ModelAdmin):
    list_display = ("seen", "device")
    list_filter = ("device__symbol", "device__district", "device__make", "device__model", "device__category")
    search_fields = ("device__deviceid", "device__name", "device__callsign", "device__rego")
    date_hierarchy = "seen"

    def change_view(self, request, obj=None):
        return HttpResponseRedirect(reverse('admin:tracking_loggedpoint_changelist'))
