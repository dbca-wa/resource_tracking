from __future__ import absolute_import, unicode_literals
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render_to_response
import requests

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


def device_csv(request):
    """Query the Device API CSV endpoint, return a file attachment.
    """
    api_url = reverse('api_dispatch_list', kwargs={'api_name': 'v1', 'resource_name': 'device'})
    params = {'limit': 10000, 'format': 'csv'}
    # Allow filtering by ``seen_age__lte=<minutes>`` query param
    if 'seen_age__lte' in request.GET:
        params['seen_age__lte'] = request.GET['seen_age__lte']
    r = requests.get(request.build_absolute_uri(api_url), params=params)

    if not r.status_code == 200:
        r.raise_for_status()

    response = HttpResponse(r.content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=tracking_devices.csv'
    return response
