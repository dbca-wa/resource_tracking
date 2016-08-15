from __future__ import absolute_import, unicode_literals
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render_to_response
import requests
import json

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
    r = requests.get(request.build_absolute_uri(api_url), params=params, cookies=request.COOKIES)

    if not r.status_code == 200:
        r.raise_for_status()

    response = HttpResponse(r.content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=tracking_devices.csv'
    return response

def get_vehicles(request):
    if request.is_ajax():
        term = request.GET.get('term','')
        r = requests.get(settings.KMI_VEHICLE_BASE_URL + "&CQL_FILTER=rego%20ilike%20%27%25"+term+"%25%27", auth=(settings.EMAIL_USER,settings.EMAIL_PASSWORD))
        vehicle_features = json.loads(r.content).get('features')
        results = []
        for vehicle in vehicle_features:
            vehicle_json = {}
            vehicle_json['value'] = vehicle.get('properties').get('rego')
            vehicle_json['label'] = vehicle.get('properties').get('rego') + ', ' + vehicle.get('properties').get('make_desc') +', '+\
                vehicle.get('properties').get('model_desc') +', '+ vehicle.get('properties').get('category_desc')
            results.append(vehicle_json)
        data = json.dumps(results)
    else:
        data = ''
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)
