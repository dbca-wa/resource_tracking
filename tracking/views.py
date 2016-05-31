from __future__ import absolute_import, unicode_literals
from django.shortcuts import render_to_response
from django.conf import settings

from tracking.models import Device


def index(request):
    return render_to_response("index.html", {
        "settings": settings,
        "user": request.user
    })


def print_map(request):
    return render_to_response("print.html", {
        "settings": settings
    })


def device(request, device_id):
    return render_to_response("device.html", {
        "device": Device.objects.get(pk=device_id)
    })
