from __future__ import absolute_import, unicode_literals
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render_to_response
from datetime import datetime, timedelta
from tracking.models import LoggedPoint
import requests
import json
import unicodecsv
import pytz

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
    today = datetime.today()
    api_url = reverse('api_dispatch_list', kwargs={'api_name': 'v1', 'resource_name': 'device'})
    params = {'limit': 10000, 'format': 'csv'}
    # Allow filtering by ``seen_age__lte=<minutes>`` query param
    if 'deviceid__in' in request.GET:
        params['deviceid__in'] = request.GET['deviceid__in']
    if 'seen_age__lte' in request.GET:
        params['seen_age__lte'] = request.GET['seen_age__lte']
    r = requests.get(request.build_absolute_uri(api_url), params=params, cookies=request.COOKIES)

    if not r.status_code == 200:
        r.raise_for_status()

    response = HttpResponse(r.content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=tracking_devices_' + datetime.strftime(datetime.today(),"%Y-%m-%d_%H%M") + '.csv'
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


def export_stop_start_points(request):

    query_list = []
    try:
        fromdate = request.GET['fromdate']
    except:
        fromdate = None
    try:
        todate = request.GET['todate']
    except:
        todate = None

    if fromdate and todate:
        try:
            fromdate = pytz.timezone("Australia/Perth").localize(datetime.strptime(fromdate, '%d-%m-%Y'))
            fromdate = fromdate.astimezone(pytz.UTC)
            todate = pytz.timezone("Australia/Perth").localize(datetime.strptime(todate, '%d-%m-%Y'))
            todate = todate.astimezone(pytz.UTC)
        except:
            pass
    elif fromdate:
        try:
            fromdate = pytz.timezone("Australia/Perth").localize(datetime.strptime(fromdate, '%d-%m-%Y'))
            fromdate = fromdate.astimezone(pytz.UTC)
            todate = fromdate + timedelta(days=30)
        except:
            pass
    elif todate:
        try:
            todate = pytz.timezone("Australia/Perth").localize(datetime.strptime(todate, '%d-%m-%Y'))
            todate = todate.astimezone(pytz.UTC)
            fromdate = todate + timedelta(days=-30)
        except:
            pass
    else:
        fromdate = pytz.utc.localize(datetime.utcnow()) + timedelta(days=-30)
        todate = pytz.utc.localize(datetime.utcnow())

    fromdatetext = fromdate.astimezone(pytz.timezone("Australia/Perth"))
    todatetext = todate.astimezone(pytz.timezone("Australia/Perth"))
    filename = 'SSS_LoggedPoint_{}-{}.csv'.format(fromdatetext.strftime('%Y%m%d'), todatetext.strftime('%Y%m%d'))
    points = LoggedPoint.objects.filter(seen__gte=fromdate,seen__lte=todate,message__in=(1,2,25,26)).order_by('seen')

    for p in points:
        seen = datetime.strftime(p.seen.astimezone(pytz.timezone("Australia/Perth")), "%d-%m-%Y %H:%M:%S")
        device_id = p.device.deviceid
        message = p.get_message_display()
        latitude = p.point.y
        longitude = p.point.x
        vehicle_id = p.device.callsign
        rego = p.device.name
        district = p.device.get_district_display()
        symbol = p.device.get_symbol_display()

        query_list.append([seen, device_id, message, latitude, longitude, vehicle_id, rego, district, symbol])

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    writer = unicodecsv.writer(response, quoting=unicodecsv.QUOTE_ALL)
    writer.writerow(["Seen", "DeviceID", "Message", "Latitude", "Longitude", "VehicleID", "Rego", "District", "Symbol"])

    for row in query_list:
        writer.writerow([unicode(s).encode("utf-8") for s in row])

    return response
