from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import force_text
from django.db import connections

import csv
import time
import pytz
import json
import email
import struct
import logging
import requests
from imaplib import IMAP4_SSL
from datetime import datetime, timedelta
from dateutil.parser import parse

from tracking.models import Device, LoggedPoint

LOGGER = logging.getLogger('tracking_points')
BATCH_SIZE = 600


class DeferredIMAP(object):
    '''
    Convenience class for maintaining
    a bit of state about an IMAP server
    and handling logins/logouts.
    Note instances aren't threadsafe.
    '''
    def __init__(self, host, user, password):
        self.deletions = []
        self.flags = []
        self.host = host
        self.user = user
        self.password = password

    def login(self):
        self.imp = IMAP4_SSL(self.host)
        self.imp.login(self.user, self.password)
        self.imp.select("INBOX")

    def logout(self, expunge=False):
        if expunge:
            self.imp.expunge
        self.imp.close()
        self.imp.logout()

    def flush(self):
        self.login()
        if self.flags:
            LOGGER.info("Flagging {} unprocessable emails.".format(len(self.flags)))
            self.imp.store(",".join(self.flags), '+FLAGS', r'(\Flagged)')
        if self.deletions:
            LOGGER.info("Deleting {} processed emails.".format(len(self.deletions)))
            self.imp.store(",".join(self.deletions), '+FLAGS', r'(\Deleted)')
            self.logout(expunge=True)
        else:
            self.logout()
        self.flags, self.deletions = [], []

    def delete(self, msgid):
        self.deletions.append(str(msgid))

    def flag(self, msgid):
        self.flags.append(str(msgid))

    def __getattr__(self, name):
        def temp(*args, **kwargs):
            self.login()
            result = getattr(self.imp, name)(*args, **kwargs)
            self.logout()
            return result
        return temp


def retrieve_emails(dimap, search):
    textids = dimap.search(None, search)[1][0].decode("utf-8").split(' ')
    # If no emails just return
    if textids == ['']:
        return []
    typ, responses = dimap.fetch(",".join(textids[-BATCH_SIZE:]), '(BODY.PEEK[])')
    # If protcol error just return
    if typ != 'OK':
        return []
    messages = []
    for response in responses:
        if isinstance(response, tuple):
            resp_decoded_msgid = response[0].decode("utf-8")
            resp_decoded_msg = response[1].decode("utf-8")
            msgid = int(resp_decoded_msgid.split(' ')[0])
            msg = email.message_from_string(resp_decoded_msg)
            messages.append((msgid, msg))
    LOGGER.info("Fetched {}/{} messages for {}.".format(len(messages), len(textids), search))
    return messages


def lat_long_isvalid(lt, lg):
    return (lt <= 90 and lt >= -90 and lg <= 180 and lg >= -180)


def save_iriditrak(dimap, queueitem):
    msgid, msg = queueitem
    try:
        deviceid = int(msg["SUBJECT"].replace('SBD Msg From Unit: ', ''))
    except ValueError:
        dimap.flag(msgid)
        return
    attachment = None
    for part in msg.walk():
        if part.get_content_maintype() != 'multipart':
            attachment = part.get_payload(decode=True)
    # Make sure email is from iridium and has valid timestamp
    received = filter(lambda val: val.find("(HELO sbd.iridium.com)") > -1, msg.values())
    if 'DATE' in msg:
        timestamp = time.mktime(email.utils.parsedate(msg["DATE"]))
    elif len(received) == 1:
        timestamp = time.mktime(email.utils.parsedate(received[0].split(';')[-1].strip()))
    else:
        LOGGER.info("Can't find date in " + str(msg.__dict__))
    sbd = {'ID': deviceid, 'TU': timestamp, 'TY': 'iriditrak'}
    # BEAM binary message, 10byte or 20byte
    if len(attachment) <= 20:
        try:
            raw = struct.unpack("<BBBBBBBBBBIHHH"[:len(attachment) + 1], attachment)
            # Byte 1 Equation byte, use to detect type of message
            sbd['EQ'] = raw[0]
            # BEAM 10byte and 20byte binary messages
            if sbd['EQ'] in [1, 2, 3, 4, 18, 19, 25, 26]:
                # Byte 2: SSSS:GPS:Lat:Lng:Msd (SSSS = SQ, Msd = Most Significant Digit of Longitude)
                sbd['SQ'] = int('0' + bin(raw[1])[2:][-8:-4], 2)
                Lat = int(bin(raw[1])[2:][-3]) * '-'
                Lng = int(bin(raw[1])[2:][-2]) * '-'
                LngH = bin(raw[1])[2:][-1]
                # Byte 3,4 (Latitude HHMM)
                LatH = str(int('0' + bin(raw[2])[2:][-4:], 2)) + str(int('0' + bin(raw[2])[2:][-8:-4], 2))
                LatM = str(int('0' + bin(raw[3])[2:][-4:], 2)) + str(int('0' + bin(raw[3])[2:][-8:-4], 2))
                # Byte 5,6 (Latitude .MMMM)
                LatM += '.' + str(int('0' + bin(raw[4])[2:][-4:], 2)) + str(int('0' + bin(raw[4])[2:][-8:-4], 2))
                LatM += str(int('0' + bin(raw[5])[2:][-4:], 2)) + str(int('0' + bin(raw[5])[2:][-8:-4], 2))
                sbd['LT'] = float(Lat + str(int(LatH) + float(LatM) / 60))
                # Byte 7,8 (Longitude HHMM)
                LngH += str(int('0' + bin(raw[6])[2:][-4:], 2)) + str(int('0' + bin(raw[6])[2:][-8:-4], 2))
                LngM = str(int('0' + bin(raw[7])[2:][-4:], 2)) + str(int('0' + bin(raw[7])[2:][-8:-4], 2))
                # Byte 9,10 (Longitude .MMMM)
                LngM += '.' + str(int('0' + bin(raw[8])[2:][-4:], 2)) + str(int('0' + bin(raw[8])[2:][-8:-4], 2))
                LngM += str(int('0' + bin(raw[9])[2:][-4:], 2)) + str(int('0' + bin(raw[9])[2:][-8:-4], 2))
                sbd['LG'] = float(Lng + str(int(LngH) + float(LngM) / 60))
                if not lat_long_isvalid(sbd['LT'], sbd['LG']):
                    raise ValueError('Lon/Lat {},{} is not valid.'.format(sbd['LG'], sbd['LT']))
                if len(raw) == 14:
                    # Byte 11,12,13,14 is unix time, but local to the device??
                    # use email timestamp because within 10 secs and fairly accurate
                    # might have future issues with delayed retransmits
                    sbd['LOCALTU'] = raw[10]
                    # Byte 15,16 are speed in 10 m/h
                    sbd['VL'] = raw[11] * 10
                    # Byte 17,18 is altitude in m above sea level
                    sbd['AL'] = raw[12]
                    # Byte 19,20 is direction in degrees
                    sbd['DR'] = raw[13]
                LOGGER.debug(str(sbd))
            else:
                LOGGER.warning("Don't know how to read " + force_text(sbd['EQ']) + " - " + force_text(raw))
                dimap.flag(msgid)
                return
        except Exception as e:
            LOGGER.error(force_text(e))
            dimap.flag(msgid)
            return
    else:
        LOGGER.warning("Flagging IridiTrak message {}".format(msgid))
        dimap.flag(msgid)
        return

    LoggedPoint.parse_sbd(sbd)
    dimap.delete(msgid)


def save_dplus(dimap, queueitem):
    msgid, msg = queueitem
    sbd = {"RAW": msg.get_payload().strip().split("|")}
    try:
        deviceid = sbd["ID"] = int(sbd["RAW"][0])
        sbd["LT"] = float(sbd["RAW"][4])
        sbd["LG"] = float(sbd["RAW"][5])
        if not lat_long_isvalid(sbd['LT'], sbd['LG']):
            raise ValueError('Lon/Lat {},{} is not valid.'.format(sbd['LG'], sbd['LT']))
        sbd["TU"] = time.mktime(datetime.strptime(sbd["RAW"][1], "%d-%m-%y %H:%M:%S").timetuple())
        sbd["VL"] = int(sbd["RAW"][6]) * 1000
        sbd["DR"] = int(sbd["RAW"][7])
        sbd["AL"] = int(sbd["RAW"][9])
        sbd["TY"] = 'dplus'
    except ValueError as e:
        LOGGER.error(e)
        dimap.flag(msgid)
        return
    try:
        LoggedPoint.parse_sbd(sbd)
    except Exception as e:
        LOGGER.error(e)
        dimap.flag(msgid)
        return

    dimap.delete(msgid)


def save_spot(dimap, queueitem):
    msgid, msg = queueitem
    if 'DATE' in msg:
        timestamp = time.mktime(email.utils.parsedate(msg["DATE"]))
    else:
        LOGGER.info("Can't find date in " + str(msg.__dict__))
        dimap.flag(msgid)
        return
    try:
        sbd = {
            'ID': msg['X-SPOT-Messenger'],
            'LT': float(msg['X-SPOT-Latitude']),
            'LG': float(msg['X-SPOT-Longitude']),
            'Type': msg['X-SPOT-Type'],
            'LOCALTU': msg['X-Spot-Time'],
            'TU': timestamp,
            'DR': 0,
            'AL': 0,
            'VL': 0,
            'TY': 'spot'
        }
        if not lat_long_isvalid(sbd['LT'], sbd['LG']):
            raise ValueError('Lon/Lat {},{} is not valid.'.format(sbd['LG'], sbd['LT']))
    except ValueError as e:
        LOGGER.error("Couldn't parse {}, error: {}".format(sbd, e))
        dimap.flag(msgid)
        return
    LoggedPoint.parse_sbd(sbd)
    dimap.delete(msgid)


def save_tracplus():
    if not settings.TRACPLUS_URL:
        return
    symbol_map = {
        'Aircraft': 'spotter aircraft',
        'Helicopter': 'rotary aircraft',
    }
    content = requests.get(settings.TRACPLUS_URL).content.decode('utf-8')
    latest = list(csv.DictReader(content.split('\r\n')))
    updated = 0
    for row in latest:
        device = Device.objects.get_or_create(deviceid=row["Device IMEI"])[0]
        device.callsign = row["Asset Name"]
        device.callsign_display = row["Asset Name"]
        device.model = row["Asset Model"]
        device.registration = row["Asset Regn"][:32]
        device.velocity = int(row["Speed"]) * 1000
        device.altitude = row["Altitude"]
        device.heading = row["Track"]
        device.seen = timezone.make_aware(datetime.strptime(row["Transmitted"], "%Y-%m-%d %H:%M:%S"), pytz.timezone("UTC"))
        device.point = "POINT ({} {})".format(row["Longitude"], row["Latitude"])
        device.source_device_type = 'tracplus'
        if row['Asset Type'] in symbol_map:
            device.symbol = symbol_map[row['Asset Type']]
        device.save()
        lp, new = LoggedPoint.objects.get_or_create(device=device, seen=device.seen)
        lp.velocity = device.velocity
        lp.heading = device.heading
        lp.altitude = device.altitude
        lp.point = device.point
        lp.seen = device.seen
        lp.source_device_type = device.source_device_type
        lp.raw = json.dumps(row)
        lp.save()
        if new:
            updated += 1
    LOGGER.info("Updated {} of {} scanned TracPLUS devices".format(updated, len(latest)))


def save_fleetcare_db():
    cursor = connections['fcare'].cursor()
    cursor.execute("select * from logentry limit 20000")
    harvested, ignored, updated, created = 0, 0, 0, 0
    rows = cursor.fetchall()
    for rowid, filename, blobtime, jsondata in rows:
        try:
            data = json.loads(jsondata)
            assert data["format"] == "dynamics"
            deviceid = "fc_" + data["vehicleID"]
        except Exception as e:
            LOGGER.error("{}: {}".format(rowid, e))
            continue
        harvested += 1
        seen = timezone.make_aware(parse(data['timestamp']))
        device, isnew = Device.objects.get_or_create(deviceid=deviceid)
        if isnew: created += 1
        updated += 1
        device.point = "POINT ({} {})".format(*data['GPS']['coordinates'])
        if device.seen and seen > device.seen:
            device.seen = seen
        device.registration = data["vehicleRego"]
        device.velocity = int(float(data["readings"]["vehicleSpeed"]) * 1000)
        device.altitude = int(float(data["readings"]["vehicleAltitude"]))
        device.heading = int(float(data["readings"]["vehicleHeading"]))
        device.source_device_type = 'fleetcare'
        device.save()
        lp, new = LoggedPoint.objects.get_or_create(device=device, seen=device.seen)
        if not new: ignored += 1 # Already harvested, save anyway
        lp.velocity = device.velocity
        lp.heading = device.heading
        lp.altitude = device.altitude
        lp.point = device.point
        lp.seen = device.seen
        lp.source_device_type = device.source_device_type
        lp.raw = jsondata
        lp.save()
        cursor.execute("delete from logentry where id = %s", [rowid])
    return harvested, created, updated, ignored


def save_dfes_avl():
    LOGGER.info('Harvest DFES API started, out of order buffer is {} seconds'.format(settings.DFES_OUT_OF_ORDER_BUFFER))
    latest = requests.get(url=settings.DFES_URL, auth=requests.auth.HTTPBasicAuth(settings.DFES_USER, settings.DFES_PASS)).json()['features']
    LOGGER.info('Harvest DFES API complete')

    latest_seen = None
    try:
        latest_seen = Device.objects.filter(source_device_type='dfes', seen__lt=timezone.now()).latest('seen').seen
    except ObjectDoesNotExist:
        pass
    # Can't gurantee that messages send by the vechicle will enter into the database in order,
    # so add 5 minutes to allow disordered message will not be ignored within 5 minutes
    earliest_seen = None
    if latest_seen:
        earliest_seen = latest_seen - timedelta(seconds=settings.DFES_OUT_OF_ORDER_BUFFER)

    ignored = 0
    updated = 0
    created = 0
    harvested = 0
    for row in latest:
        if row['type'] == 'Feature':
            harvested += 1
            prop = row["properties"]
            if not prop["Time"]:
                # Time is null, should be a illegal value, ignore it
                ignored += 1
                continue
            seen = timezone.make_aware(datetime.strptime(prop["Time"], "%Y-%m-%dT%H:%M:%S.%fZ"), pytz.timezone("UTC"))
            if earliest_seen and seen < earliest_seen:
                # Already harvested.
                ignored += 1
                continue
            elif latest_seen is None:
                latest_seen = seen
            elif seen > latest_seen:
                latest_seen = seen
            deviceid = str(prop["TrackerID"]).strip()
            try:
                device = Device.objects.get(deviceid=deviceid)
                if seen == device.seen:
                    # Already harvested.
                    ignored += 1
                    continue
                updated += 1
            except ObjectDoesNotExist:
                device = Device(deviceid=deviceid)
                created += 1

            device.callsign = prop["VehicleName"]
            device.callsign_display = prop["VehicleName"]
            device.model = prop["Model"]
            device.registration = 'DFES - ' + prop["Registration"][:32]
            device.symbol = (prop["VehicleType"]).strip()
            if device.symbol in ['2.4 BROADACRE', '2.4 RURAL', '3.4', '4.4', '1.4 RURAL', '2.4 URBAN', '3.4 RURAL', '3.4 SSSBFT', '3.4 URBAN', '4.4 BROADACRE', '4.4 RURAL']:
                device.symbol = 'gang truck'
            elif device.symbol == 'LIGHT TANKER':
                device.symbol = 'light unit'
            elif device.symbol in ['BUS 10 SEATER', 'BUS 21 SEATER', 'BUS 22 SEATER', 'INCIDENT CONTROL VEHICLE', 'MINI BUS 12 SEATER']:
                device.symbol = 'comms bus'
            elif device.symbol in ['GENERAL RESCUE TRUCK', 'HAZMAT STRUCTURAL RESCUE', 'RESCUE VEHICLE', 'ROAD CRASH RESCUE TRUCK', 'SPECIALIST EQUIPMENT TENDER', 'TRUCK']:
                device.symbol = 'tender'
            elif device.symbol in ['Crew Cab Utility w canopy', 'FIRST RESPONSE UNIT', 'FIRST RESPONSE VEHICLE', 'UTILITY', 'Utility']:
                device.symbol = '4 wheel drive ute'
            elif device.symbol in ['CAR (4WD)', 'PERSONNEL CARRIER', 'PERSONNEL CARRIER 11 SEATER', 'PERSONNEL CARRIER 5 SEATER', 'PERSONNEL CARRIER 6 SEATER']:
                device.symbol = '4 wheel drive passenger'
            elif device.symbol == 'CAR':
                device.symbol = '2 wheel drive'
            else:
                device.symbol = 'unknown'
            if device.registration.strip() == 'DFES -':
                device.registration = 'DFES - No Rego'
            device.velocity = int(prop["Speed"]) * 1000
            device.heading = prop["Direction"]
            device.seen = seen
            device.point = "POINT ({} {})".format(row['geometry']['coordinates'][0], row['geometry']['coordinates'][1])
            device.source_device_type = 'dfes'
            device.save()

            LoggedPoint.objects.create(
                device=device,
                seen=device.seen,
                velocity=device.velocity,
                heading=device.heading,
                point=device.point,
                source_device_type=device.source_device_type,
                raw=json.dumps(row)
            )

    LOGGER.info("Harvested {} from DFES: created {}, updated {}, ignored {}, earliest seen {}, latest seen {}.".format(
        harvested, created, updated, ignored, earliest_seen, latest_seen))

    return harvested, created, updated, ignored, earliest_seen, latest_seen


def save_mp70(dimap, queueitem):
    '''
    mp70/rv50 device type using comma separated output
    Sample email content and associated fields:
        Device_ID, Battery_Voltage, Latitude, Longitude, Speed_km/h, Heading, Time_UTC
        N681260193011034,12.09,-031.99275,+115.88458,0,0,01/11/2019 06:57:40
    '''
    msgid, msg = queueitem
    sbd = {"RAW": msg.get_payload().strip().split(",")}
    try:
        sbd["ID"] = sbd["RAW"][0]
        sbd["LT"] = float(sbd["RAW"][2])
        sbd["LG"] = float(sbd["RAW"][3])
        if not lat_long_isvalid(sbd['LT'], sbd['LG']):
            raise ValueError('Lon/Lat {},{} is not valid.'.format(sbd['LG'], sbd['LT']))
        sbd["TU"] = time.mktime(datetime.strptime(sbd["RAW"][6], "%m/%d/%Y %H:%M:%S").timetuple())
        sbd["VL"] = int(sbd["RAW"][4])
        sbd["DR"] = int(sbd["RAW"][5])
        sbd["TY"] = 'other'
    except ValueError as e:
        LOGGER.error(e)
        dimap.flag(msgid)
        return
    try:
        LoggedPoint.parse_sbd(sbd)
    except Exception as e:
        LOGGER.error(e)
        dimap.flag(msgid)
        return
    dimap.delete(msgid)


def harvest_tracking_email(request=None):
    """Download and save tracking point emails.
    """
    dimap = DeferredIMAP(
        host=settings.EMAIL_HOST, user=settings.EMAIL_USER, password=settings.EMAIL_PASSWORD)
    start = timezone.now()

    LOGGER.info('Harvesting IridiTRAK emails')
    emails = retrieve_emails(dimap, '(FROM "sbdservice@sbd.iridium.com" UNFLAGGED)')
    for message in emails:
        save_iriditrak(dimap, message)
    dimap.flush()

    LOGGER.info('Harvesting DPlus emails')
    emails = retrieve_emails(dimap, '(FROM "Dplus@asta.net.au" UNFLAGGED)')
    for message in emails:
        save_dplus(dimap, message)
    dimap.flush()

    LOGGER.info('Harvesting Spot emails')
    emails = retrieve_emails(dimap, '(FROM "noreply@findmespot.com" UNFLAGGED)')
    for message in emails:
        save_spot(dimap, message)
    dimap.flush()

    LOGGER.info('Harvesting MP70 emails')
    emails = retrieve_emails(dimap, '(FROM "sierrawireless_v1@dbca.wa.gov.au" UNFLAGGED)')
    for message in emails:
        save_mp70(dimap, message)
    dimap.flush()

    LOGGER.info('Harvesting TracPlus emails')
    try:
        save_tracplus()
    except Exception as e:
        LOGGER.error(e)

    # DFES feed handled by separate management command

    delta = timezone.now() - start
    html = "<html><body>Tracking point email harvest run at {} for {}</body></html>".format(start, delta)
    if request:
        return HttpResponse(html)
    else:
        return
