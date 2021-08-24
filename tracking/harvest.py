from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.encoding import force_text
from django.db import connections, connection, transaction
from django.contrib.gis.geos import GEOSGeometry

import csv
import time
import pytz
import json
import email
import struct
import requests
import traceback
from imaplib import IMAP4_SSL

from tracking.models import Device, LoggedPoint, InvalidLoggedPoint

BATCH_SIZE = 600


def get_fleetcare_creationtime(name):
    try:
        return timezone.make_aware(datetime.strptime(name[-24:-5], "%Y-%m-%dT%H:%M:%S"))
    except Exception as ex:
        return Exception(
            "Failed to extract datetime from fleetcare filename({}).{}".format(
                name, str(ex)
            )
        )


class DeferredIMAP(object):
    """
    Convenience class for maintaining
    a bit of state about an IMAP server
    and handling logins/logouts.
    Note instances aren't threadsafe.
    """

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
            print("Flagging {} unprocessable emails.".format(len(self.flags)))
            try:
                self.imp.store(",".join(self.flags), "+FLAGS", r"(\Flagged)")
            except Exception:
                print("Unable to flag messageset {}".format(",".join(self.flags)))
        if self.deletions:
            print("Deleting {} processed emails.".format(len(self.deletions)))
            try:
                self.imp.store(",".join(self.deletions), "+FLAGS", r"(\Deleted)")
            except Exception:
                print("Unable to delete messageset {}".format(",".join(self.deletions)))
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
    textids = dimap.search(None, search)[1][0].decode("utf-8").split(" ")
    # If no emails just return
    if textids == [""]:
        return []
    try:
        typ, responses = dimap.fetch(",".join(textids[-BATCH_SIZE:]), "(BODY.PEEK[])")
    except Exception as e:
        print(e)
        print("Unable to fetch messageset {}".format(",".join(textids[-BATCH_SIZE:])))
        return []
    # If protocol error, just return.
    if typ != "OK":
        return []
    messages = []
    for response in responses:
        if isinstance(response, tuple):
            resp_decoded_msgid = response[0].decode("utf-8")
            resp_decoded_msg = response[1].decode("utf-8")
            msgid = int(resp_decoded_msgid.split(" ")[0])
            msg = email.message_from_string(resp_decoded_msg)
            messages.append((msgid, msg))
    print("Fetched {}/{} messages for {}.".format(len(messages), len(textids), search))
    return messages


def lat_long_isvalid(lt, lg):
    return lt <= 90 and lt >= -90 and lg <= 180 and lg >= -180


def save_iriditrak(dimap, queueitem):
    msgid, msg = queueitem
    try:
        deviceid = int(msg["SUBJECT"].replace("SBD Msg From Unit: ", ""))
    except ValueError:
        dimap.flag(msgid)
        return False
    attachment = None
    for part in msg.walk():
        if part.get_content_maintype() != "multipart":
            attachment = part.get_payload(decode=True)
    # Make sure email is from iridium and has valid timestamp
    received = filter(lambda val: val.find("(HELO sbd.iridium.com)") > -1, msg.values())
    if "DATE" in msg:
        timestamp = time.mktime(email.utils.parsedate(msg["DATE"]))
    elif len(received) == 1:
        timestamp = time.mktime(
            email.utils.parsedate(received[0].split(";")[-1].strip())
        )
    else:
        print("Can't find date in " + str(msg.__dict__))
    sbd = {"ID": deviceid, "TU": timestamp, "TY": "iriditrak"}
    # BEAM binary message, 10byte or 20byte
    if len(attachment) <= 20:
        try:
            raw = struct.unpack("<BBBBBBBBBBIHHH"[: len(attachment) + 1], attachment)
            # Byte 1 Equation byte, use to detect type of message
            sbd["EQ"] = raw[0]
            # BEAM 10byte and 20byte binary messages
            if sbd["EQ"] in [1, 2, 3, 4, 18, 19, 25, 26]:
                # Byte 2: SSSS:GPS:Lat:Lng:Msd (SSSS = SQ, Msd = Most Significant Digit of Longitude)
                sbd["SQ"] = int("0" + bin(raw[1])[2:][-8:-4], 2)
                Lat = int(bin(raw[1])[2:][-3]) * "-"
                Lng = int(bin(raw[1])[2:][-2]) * "-"
                LngH = bin(raw[1])[2:][-1]
                # Byte 3,4 (Latitude HHMM)
                LatH = str(int("0" + bin(raw[2])[2:][-4:], 2)) + str(
                    int("0" + bin(raw[2])[2:][-8:-4], 2)
                )
                LatM = str(int("0" + bin(raw[3])[2:][-4:], 2)) + str(
                    int("0" + bin(raw[3])[2:][-8:-4], 2)
                )
                # Byte 5,6 (Latitude .MMMM)
                LatM += (
                    "."
                    + str(int("0" + bin(raw[4])[2:][-4:], 2))
                    + str(int("0" + bin(raw[4])[2:][-8:-4], 2))
                )
                LatM += str(int("0" + bin(raw[5])[2:][-4:], 2)) + str(
                    int("0" + bin(raw[5])[2:][-8:-4], 2)
                )
                sbd["LT"] = float(Lat + str(int(LatH) + float(LatM) / 60))
                # Byte 7,8 (Longitude HHMM)
                LngH += str(int("0" + bin(raw[6])[2:][-4:], 2)) + str(
                    int("0" + bin(raw[6])[2:][-8:-4], 2)
                )
                LngM = str(int("0" + bin(raw[7])[2:][-4:], 2)) + str(
                    int("0" + bin(raw[7])[2:][-8:-4], 2)
                )
                # Byte 9,10 (Longitude .MMMM)
                LngM += (
                    "."
                    + str(int("0" + bin(raw[8])[2:][-4:], 2))
                    + str(int("0" + bin(raw[8])[2:][-8:-4], 2))
                )
                LngM += str(int("0" + bin(raw[9])[2:][-4:], 2)) + str(
                    int("0" + bin(raw[9])[2:][-8:-4], 2)
                )
                sbd["LG"] = float(Lng + str(int(LngH) + float(LngM) / 60))
                if not lat_long_isvalid(sbd["LT"], sbd["LG"]):
                    raise ValueError(
                        "Lon/Lat {},{} is not valid.".format(sbd["LG"], sbd["LT"])
                    )
                if len(raw) == 14:
                    # Byte 11,12,13,14 is unix time, but local to the device??
                    # use email timestamp because within 10 secs and fairly accurate
                    # might have future issues with delayed retransmits
                    sbd["LOCALTU"] = raw[10]
                    # Byte 15,16 are speed in 10 m/h
                    sbd["VL"] = raw[11] * 10
                    # Byte 17,18 is altitude in m above sea level
                    sbd["AL"] = raw[12]
                    # Byte 19,20 is direction in degrees
                    sbd["DR"] = raw[13]
            else:
                print(
                    "Error: don't know how to read "
                    + force_text(sbd["EQ"])
                    + " - "
                    + force_text(raw)
                )
                dimap.flag(msgid)
                return False
        except Exception as e:
            print(force_text(e))
            dimap.flag(msgid)
            return False
    else:
        print("Flagging IridiTrak message {}".format(msgid))
        dimap.flag(msgid)
        return False

    point = LoggedPoint.parse_sbd(sbd)
    dimap.delete(msgid)
    return point


def save_dplus(dimap, queueitem):
    msgid, msg = queueitem
    sbd = {"RAW": msg.get_payload().strip().split("|")}
    try:
        sbd["ID"] = int(sbd["RAW"][0])
        sbd["LT"] = float(sbd["RAW"][4])
        sbd["LG"] = float(sbd["RAW"][5])
        if not lat_long_isvalid(sbd["LT"], sbd["LG"]):
            raise ValueError("Lon/Lat {},{} is not valid.".format(sbd["LG"], sbd["LT"]))
        sbd["TU"] = time.mktime(
            datetime.strptime(sbd["RAW"][1], "%d-%m-%y %H:%M:%S").timetuple()
        )
        sbd["VL"] = int(sbd["RAW"][6]) * 1000
        sbd["DR"] = int(sbd["RAW"][7])
        sbd["AL"] = int(sbd["RAW"][9])
        sbd["TY"] = "dplus"
    except ValueError as e:
        print(e)
        dimap.flag(msgid)
        return False
    try:
        point = LoggedPoint.parse_sbd(sbd)
        dimap.delete(msgid)
        return point
    except Exception as e:
        print(e)
        dimap.flag(msgid)
        return False


def save_spot(dimap, queueitem):
    msgid, msg = queueitem
    if "DATE" in msg:
        timestamp = time.mktime(email.utils.parsedate(msg["DATE"]))
    else:
        print("Can't find date in " + str(msg.__dict__))
        dimap.flag(msgid)
        return False
    try:
        sbd = {
            "ID": msg["X-SPOT-Messenger"],
            "LT": float(msg["X-SPOT-Latitude"]),
            "LG": float(msg["X-SPOT-Longitude"]),
            "Type": msg["X-SPOT-Type"],
            "LOCALTU": msg["X-Spot-Time"],
            "TU": timestamp,
            "DR": 0,
            "AL": 0,
            "VL": 0,
            "TY": "spot",
        }
        if not lat_long_isvalid(sbd["LT"], sbd["LG"]):
            raise ValueError("Lon/Lat {},{} is not valid.".format(sbd["LG"], sbd["LT"]))
    except ValueError as e:
        print("Error: couldn't parse {}, error: {}".format(sbd, e))
        dimap.flag(msgid)
        return False

    point = LoggedPoint.parse_sbd(sbd)
    dimap.delete(msgid)
    return point


tracplus_symbol_map = {
    "Aircraft": "spotter aircraft",
    "Helicopter": "rotary aircraft",
}


def save_tracplus():
    if not settings.TRACPLUS_URL:
        return False

    content = requests.get(settings.TRACPLUS_URL).content.decode("utf-8")
    latest = list(csv.DictReader(content.split("\r\n")))
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
        device.seen = timezone.make_aware(
            datetime.strptime(row["Transmitted"], "%Y-%m-%d %H:%M:%S"),
            pytz.timezone("UTC"),
        )
        device.point = "POINT ({} {})".format(row["Longitude"], row["Latitude"])
        device.source_device_type = "tracplus"
        device.deleted = False
        if row["Asset Type"] in tracplus_symbol_map:
            device.symbol = tracplus_symbol_map[row["Asset Type"]]
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
    return (updated, len(latest))


fleetcare_dt_patterns = [
    "%d/%m/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y/%m/&d %I:%M:%S %p",
]
fleetcare_max_blob_creation_delay = timedelta(days=1)


def save_fleetcare_db(
    staging_table="logentry",
    loggedpoint_model=LoggedPoint,
    limit=20000,
    from_dt=None,
    to_dt=None,
):
    """
    Used by havester job to harvest data from staging table (logentry) to LoggedPoint, and update Device
    Used by reharvester logic to harvest data from other staging table to other loggedpoint table , and update device
    from_dt: only reharvest the data which seen is greater than or equal with from_dt, if not None
    to_dt: only reharvest the data which seen is less than to_dt, if not None
    """

    if staging_table == "logentry":
        # in harvest mode, the target model must be LoggedPoint, and from_dt and to_dt must be None
        loggedpoint_model = LoggedPoint
        from_dt = None
        to_dt = None

    index = 0
    diff = None
    min_diff = None
    date_format_index = None
    dt = None
    seen = None

    harvested, overriden, updated, created, errors, suspicious, skipped = (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    with connections["fcare"].cursor() as cursor:
        cursor.execute(
            "select * from {} order by id limit {}".format(staging_table, limit)
        )
        rows = cursor.fetchall()
        for rowid, filename, blobtime, jsondata in rows:
            try:
                data = json.loads(jsondata)
                assert data["format"] == "dynamics"
                assert data["timestamp"]
                assert (
                    data["GPS"]["coordinates"] and len(data["GPS"]["coordinates"]) == 2
                )
                assert data["readings"] is not None
                deviceid = "fc_" + data["vehicleID"]
            except Exception as e:
                print("Error: {}: {}".format(rowid, e))
                invalid_lp = InvalidLoggedPoint(
                    category=InvalidLoggedPoint.INVALID_RAW_DATA,
                    error_msg="Failed to parse the raw data,file ={}, staging table={}.\r\n{}".format(
                        filename, staging_table, traceback.format_exc()
                    ),
                    raw=jsondata,
                )
                invalid_lp.save()
                cursor.execute(
                    "delete from {} where id = {}".format(staging_table, rowid)
                )
                continue

            # blobtime is the creation_time or last_modified_time of blob data which is not reliable. so extract the timestamp from filename
            blobtime = get_fleetcare_creationtime(filename)
            harvested += 1

            # try to parse the timestamp string to datetime object.
            # the format of the timestamp should be 'dd/mm/yyyy HH:MM:SS AM/PM', but sometimes , it can also be 'mm/dd/yyyy HH:MM:SS AM/PM',
            # to handle this issue, the following logic try to parse the datetime with two patterns, and choose the datatime which is close to blobtime.
            # if the choosed pattern is not the prefered one, will insert a row into table 'tracking_loggedpoint_suspicious'
            # if can't parse the timestamp with all possible patterns, set the source device type to 'fleetcare_error', and also insert a row into table 'tracking_loggepoint_suspicious'
            index = 0
            diff = None
            min_diff = None
            date_format_index = None
            dt = None
            seen = None
            while index < len(fleetcare_dt_patterns):
                try:
                    dt = timezone.make_aware(
                        datetime.strptime(
                            data["timestamp"], fleetcare_dt_patterns[index]
                        )
                    )
                    if not seen:
                        seen = dt
                        min_diff = (
                            seen - blobtime if seen >= blobtime else blobtime - seen
                        )
                        date_format_index = index
                        if min_diff <= fleetcare_max_blob_creation_delay:
                            break
                    else:
                        diff = dt - blobtime if dt >= blobtime else blobtime - dt
                        if diff < min_diff:
                            min_diff = diff
                            seen = dt
                            date_format_index = index
                            if min_diff <= fleetcare_max_blob_creation_delay:
                                break
                except:
                    pass
                finally:
                    index += 1

            # check whether the data is between from_dt and to_dt
            if seen:
                if from_dt and seen < from_dt:
                    skipped += 1
                    cursor.execute(
                        "delete from {} where id = {}".format(staging_table, rowid)
                    )
                    continue
                if to_dt and seen >= to_dt:
                    skipped += 1
                    cursor.execute(
                        "delete from {} where id = {}".format(staging_table, rowid)
                    )
                    continue

            if date_format_index is None:
                # can't parse the timestamp, use blobtime as placeholder
                seen = blobtime

            future_data = seen >= (timezone.now() + settings.FUTURE_DATA_OFFSET)
            if date_format_index is None or future_data:
                errors += 1
            elif date_format_index != 0:
                suspicious += 1

            device, isnew = Device.objects.get_or_create(deviceid=deviceid)
            if isnew:  # default to hiding and restricting to dbca new vehicles
                device.hidden = True
                device.internal_only = True
                device.source_device_type = "fleetcare"
                device.save(
                    update_fields=["source_device_type", "hidden", "internal_only"]
                )
                created += 1

            point = "POINT ({} {})".format(*data["GPS"]["coordinates"])
            try:
                velocity = int(float(data["readings"]["vehicleSpeed"]) * 1000)
            except Exception as ex:
                print(
                    "{}: Invalid velocity '{}'".format(
                        deviceid, data["readings"].get("vehicleSpeed")
                    )
                )
                velocity = 0

            try:
                altitude = int(float(data["readings"]["vehicleAltitude"]))
            except Exception as ex:
                print(
                    "{}: Invalid altitude '{}'".format(
                        deviceid, data["readings"].get("vehicleAltitude")
                    )
                )
                altitude = 0

            try:
                heading = int(float(data["readings"]["vehicleHeading"]))
            except Exception as ex:
                print(
                    "{}: Invalid heading '{}'".format(
                        deviceid, data["readings"].get("vehicleHeading")
                    )
                )
                heading = 0

            # Only update device details if the tracking data timestamp was parsed successfully
            if not device.seen or seen > device.seen:
                device.source_device_type = "fleetcare"
                device.deleted = False
                device.registration = data.get("vehicleRego")
                if future_data:
                    device.save(
                        update_fields=["source_device_type", "registration", "deleted"]
                    )
                elif date_format_index is None:
                    device.save(
                        update_fields=["source_device_type", "registration", "deleted"]
                    )
                else:
                    device.seen = seen
                    device.point = point
                    device.velocity = velocity
                    device.altitude = altitude
                    device.heading = heading
                    device.save()
                    if not isnew:
                        updated += 1
            elif device.source_device_type != "fleetcare":
                device.source_device_type = "fleetcare"
                device.deleted = False
                device.save(update_fields=["source_device_type", "deleted"])
            elif device.deleted:
                device.deleted = False
                device.save(update_fields=["deleted"])

            invalid_lp = None
            if future_data:
                lp = InvalidLoggedPoint(
                    seen=seen,
                    device_id=device.id,
                    deviceid=device.deviceid,
                    category=InvalidLoggedPoint.FUTURE_DATA,
                    error_msg="This data is happened in the future.",
                )
                invalid_lp = lp
            else:
                while True:
                    lp, new = loggedpoint_model.objects.get_or_create(
                        device=device, seen=seen
                    )
                    if new:
                        break
                    elif date_format_index is None:
                        # error data
                        if lp.source_device_type == "fleetcare_error":
                            overriden += 1  # Already harvested, save anyway
                            break
                        else:
                            # alreay have a correct data with the same 'seen',add 1 seconds and try to save it again
                            seen += timedelta(milliseconds=1)
                    else:
                        overriden += 1  # Already harvested, save anyway
                        break

            lp.velocity = velocity
            lp.heading = heading
            lp.altitude = altitude
            lp.point = point
            # If we think that we have an error with the parsed date, set the source_device_type as
            # "fleetcare_error" to flag the LoggedPoint for investigation later.
            if date_format_index is None:
                lp.source_device_type = "fleetcare_error"
            else:
                lp.source_device_type = device.source_device_type
            lp.raw = jsondata
            lp.save()

            if date_format_index is None or date_format_index != 0:
                if invalid_lp:
                    invalid_lp.id = None
                else:
                    invalid_lp = InvalidLoggedPoint(
                        seen=lp.seen,
                        device_id=device.id,
                        deviceid=device.deviceid,
                        velocity=lp.velocity,
                        heading=lp.heading,
                        altitude=lp.altitude,
                        point=lp.point,
                        source_device_type=lp.source_device_type,
                        raw=lp.raw,
                    )

                if date_format_index is None:
                    invalid_lp.category = (InvalidLoggedPoint.INVALID_TIMESTAMP,)
                    invalid_lp.error_msg = "Failed to parse the timestamp({}) with patterns({}). file = {}".format(
                        data["timestamp"], fleetcare_dt_patterns, filename
                    )
                elif date_format_index != 0:
                    invalid_lp.category = (InvalidLoggedPoint.INVALID_TIMESTAMP_FORMAT,)
                    invalid_lp.error_msg = "The format of the timestamp({}) is {}, but prefer {}. file = {}".format(
                        data["timestamp"],
                        fleetcare_dt_patterns[date_format_index],
                        fleetcare_dt_patterns[0],
                        filename,
                    )

                invalid_lp.save()

            cursor.execute("delete from {} where id = {}".format(staging_table, rowid))
    return harvested, created, updated, overriden, errors, suspicious, skipped


def save_dfes_avl():
    print(
        "Query DFES API started, out of order buffer is {} seconds".format(
            settings.DFES_OUT_OF_ORDER_BUFFER
        )
    )
    latest = requests.get(
        url=settings.DFES_URL,
        auth=requests.auth.HTTPBasicAuth(settings.DFES_USER, settings.DFES_PASS),
    ).json()["features"]
    print("Query DFES API complete")

    latest_seen = None
    try:
        latest_seen = (
            Device.objects.filter(source_device_type="dfes", seen__lt=timezone.now())
            .latest("seen")
            .seen
        )
    except ObjectDoesNotExist:
        pass
    # Can't gurantee that messages send by the vechicle will enter into the database in order,
    # so add 5 minutes to allow disordered message will not be ignored within 5 minutes
    earliest_seen = None
    if latest_seen:
        earliest_seen = latest_seen - timedelta(
            seconds=settings.DFES_OUT_OF_ORDER_BUFFER
        )

    ignored = 0
    updated = 0
    created = 0
    harvested = 0
    for row in latest:
        if row["type"] == "Feature":
            harvested += 1
            prop = row["properties"]
            if not prop["Time"]:
                # Time is null, should be a illegal value, ignore it
                ignored += 1
                continue
            seen = timezone.make_aware(
                datetime.strptime(prop["Time"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                pytz.timezone("UTC"),
            )
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
            device.registration = "DFES - " + prop["Registration"][:32]
            device.symbol = (prop["VehicleType"]).strip()
            if device.symbol in [
                "2.4 BROADACRE",
                "2.4 RURAL",
                "3.4",
                "4.4",
                "1.4 RURAL",
                "2.4 URBAN",
                "3.4 RURAL",
                "3.4 SSSBFT",
                "3.4 URBAN",
                "4.4 BROADACRE",
                "4.4 RURAL",
            ]:
                device.symbol = "gang truck"
            elif device.symbol == "LIGHT TANKER":
                device.symbol = "light unit"
            elif device.symbol in [
                "BUS 10 SEATER",
                "BUS 21 SEATER",
                "BUS 22 SEATER",
                "INCIDENT CONTROL VEHICLE",
                "MINI BUS 12 SEATER",
            ]:
                device.symbol = "comms bus"
            elif device.symbol in [
                "GENERAL RESCUE TRUCK",
                "HAZMAT STRUCTURAL RESCUE",
                "RESCUE VEHICLE",
                "ROAD CRASH RESCUE TRUCK",
                "SPECIALIST EQUIPMENT TENDER",
                "TRUCK",
            ]:
                device.symbol = "tender"
            elif device.symbol in [
                "Crew Cab Utility w canopy",
                "FIRST RESPONSE UNIT",
                "FIRST RESPONSE VEHICLE",
                "UTILITY",
                "Utility",
            ]:
                device.symbol = "4 wheel drive ute"
            elif device.symbol in [
                "CAR (4WD)",
                "PERSONNEL CARRIER",
                "PERSONNEL CARRIER 11 SEATER",
                "PERSONNEL CARRIER 5 SEATER",
                "PERSONNEL CARRIER 6 SEATER",
            ]:
                device.symbol = "4 wheel drive passenger"
            elif device.symbol == "CAR":
                device.symbol = "2 wheel drive"
            else:
                device.symbol = "unknown"
            if device.registration.strip() == "DFES -":
                device.registration = "DFES - No Rego"
            device.velocity = int(prop["Speed"]) * 1000
            device.heading = prop["Direction"]
            device.seen = seen
            device.point = "POINT ({} {})".format(
                row["geometry"]["coordinates"][0], row["geometry"]["coordinates"][1]
            )
            device.source_device_type = "dfes"
            device.deleted = False
            device.save()

            LoggedPoint.objects.create(
                device=device,
                seen=device.seen,
                velocity=device.velocity,
                heading=device.heading,
                point=device.point,
                source_device_type=device.source_device_type,
                raw=json.dumps(row),
            )

    print(
        "Harvested {} from DFES: created {}, updated {}, ignored {}, earliest seen {}, latest seen {}.".format(
            harvested, created, updated, ignored, earliest_seen, latest_seen
        )
    )

    return harvested, created, updated, ignored, earliest_seen, latest_seen


def save_mp70(dimap, queueitem):
    """
    mp70/rv50 device type using comma separated output
    Sample email content and associated fields:
        Device_ID, Battery_Voltage, Latitude, Longitude, Speed_km/h, Heading, Time_UTC
        N681260193011034,12.09,-031.99275,+115.88458,0,0,01/11/2019 06:57:40
    """
    msgid, msg = queueitem
    sbd = {"RAW": msg.get_payload().strip().split(",")}
    try:
        sbd["ID"] = sbd["RAW"][0]
        sbd["LT"] = float(sbd["RAW"][2])
        sbd["LG"] = float(sbd["RAW"][3])
        if not lat_long_isvalid(sbd["LT"], sbd["LG"]):
            raise ValueError("Lon/Lat {},{} is not valid.".format(sbd["LG"], sbd["LT"]))
        sbd["TU"] = time.mktime(
            datetime.strptime(sbd["RAW"][6], "%m/%d/%Y %H:%M:%S").timetuple()
        )
        sbd["VL"] = int(sbd["RAW"][4])
        sbd["DR"] = int(sbd["RAW"][5])
        sbd["TY"] = "other"
    except Exception as e:
        print(e)
        dimap.flag(msgid)
        return False
    try:
        point = LoggedPoint.parse_sbd(sbd)
        dimap.delete(msgid)
        return point
    except Exception as e:
        print(e)
        dimap.flag(msgid)
        return False


def harvest_tracking_email(device_type=None):
    """Download and save tracking point emails."""
    dimap = DeferredIMAP(
        host=settings.EMAIL_HOST,
        user=settings.EMAIL_USER,
        password=settings.EMAIL_PASSWORD,
    )
    start = timezone.now()
    created = 0
    flagged = 0

    if device_type == "iriditrak":
        print("Harvesting IridiTRAK emails")
        emails = retrieve_emails(dimap, '(FROM "sbdservice@sbd.iridium.com" UNFLAGGED)')
        for message in emails:
            out = save_iriditrak(dimap, message)
            if out:
                created += 1
            else:
                flagged += 1
        dimap.flush()
        print("Created {} tracking points, flagged {} emails".format(created, flagged))

    if device_type == "dplus":
        print("Harvesting DPlus emails")
        emails = retrieve_emails(dimap, '(FROM "Dplus@asta.net.au" UNFLAGGED)')
        for message in emails:
            out = save_dplus(dimap, message)
            if out:
                created += 1
            else:
                flagged += 1
        dimap.flush()
        print("Created {} tracking points, flagged {} emails".format(created, flagged))

    if device_type == "spot":
        print("Harvesting Spot emails")
        emails = retrieve_emails(dimap, '(FROM "noreply@findmespot.com" UNFLAGGED)')
        for message in emails:
            out = save_spot(dimap, message)
            if out:
                created += 1
            else:
                flagged += 1
        dimap.flush()
        print("Created {} tracking points, flagged {} emails".format(created, flagged))

    if device_type == "mp70":
        print("Harvesting MP70 emails")
        emails = retrieve_emails(
            dimap, '(FROM "sierrawireless_V1@mail.lan.fyi" UNFLAGGED)'
        )
        for message in emails:
            out = save_mp70(dimap, message)
            if out:
                created += 1
            else:
                flagged += 1
        dimap.flush()
        print("Created {} tracking points, flagged {} emails".format(created, flagged))

    delta = timezone.now() - start
    print(
        "Tracking point email harvest run at {} for {} seconds".format(
            start, delta.seconds
        )
    )
    return True


def recreate_fleetcare_device_from_raw(device, raw):
    data = json.loads(raw)
    device.deviceid = "fc_" + data["vehicleID"]

    device.hidden = True
    device.internal_only = True
    device.registration = data["vehicleRego"]


def recreate_tracplus_device_from_raw(device, raw):
    data = json.loads(raw)
    device.deviceid = data["Device IMEI"]
    device.callsign = data["Asset Name"]
    device.callsign_display = data["Asset Name"]
    device.model = data["Asset Model"]
    device.registration = data["Asset Regn"][:32]
    device.deleted = True
    if data["Asset Type"] in tracplus_symbol_map:
        device.symbol = tracplus_symbol_map[data["Asset Type"]]


def recreate_sbd_device_from_raw(device, raw):
    sbd = json.loads(raw)
    device.deviceid = sbd["ID"]


def recreate_dfes_device_from_raw(device, raw):
    data = json.loads(raw)
    prop = data["properties"]
    device.deviceid = str(prop["TrackerID"]).strip()
    device.callsign = prop["VehicleName"]
    device.callsign_display = prop["VehicleName"]
    device.model = prop["Model"]
    device.registration = "DFES - " + prop["Registration"][:32]
    device.symbol = (prop["VehicleType"]).strip()
    if device.symbol in [
        "2.4 BROADACRE",
        "2.4 RURAL",
        "3.4",
        "4.4",
        "1.4 RURAL",
        "2.4 URBAN",
        "3.4 RURAL",
        "3.4 SSSBFT",
        "3.4 URBAN",
        "4.4 BROADACRE",
        "4.4 RURAL",
    ]:
        device.symbol = "gang truck"
    elif device.symbol == "LIGHT TANKER":
        device.symbol = "light unit"
    elif device.symbol in [
        "BUS 10 SEATER",
        "BUS 21 SEATER",
        "BUS 22 SEATER",
        "INCIDENT CONTROL VEHICLE",
        "MINI BUS 12 SEATER",
    ]:
        device.symbol = "comms bus"
    elif device.symbol in [
        "GENERAL RESCUE TRUCK",
        "HAZMAT STRUCTURAL RESCUE",
        "RESCUE VEHICLE",
        "ROAD CRASH RESCUE TRUCK",
        "SPECIALIST EQUIPMENT TENDER",
        "TRUCK",
    ]:
        device.symbol = "tender"
    elif device.symbol in [
        "Crew Cab Utility w canopy",
        "FIRST RESPONSE UNIT",
        "FIRST RESPONSE VEHICLE",
        "UTILITY",
        "Utility",
    ]:
        device.symbol = "4 wheel drive ute"
    elif device.symbol in [
        "CAR (4WD)",
        "PERSONNEL CARRIER",
        "PERSONNEL CARRIER 11 SEATER",
        "PERSONNEL CARRIER 5 SEATER",
        "PERSONNEL CARRIER 6 SEATER",
    ]:
        device.symbol = "4 wheel drive passenger"
    elif device.symbol == "CAR":
        device.symbol = "2 wheel drive"
    else:
        device.symbol = "unknown"
    if device.registration.strip() == "DFES -":
        device.registration = "DFES - No Rego"


def recreate_device_from_raw(condition=None):
    failed_devices = []
    recreated_devices = []
    update_devices = []

    with connection.cursor() as cursor:
        if condition:
            cursor.execute(
                "select distinct a.device_id from (select * from tracking_loggedpoint where {}) a left join tracking_device b on a.device_id = b.id where b.id is null".format(
                    condition
                )
            )
        else:
            cursor.execute(
                "select distinct a.device_id from tracking_loggedpoint a left join tracking_device b on a.device_id = b.id where b.id is null"
            )
        rows = cursor.fetchall()
        device_ids = []
        for row in rows:
            device_ids.append(int(row[0]))

        for device_id in device_ids:
            cursor.execute(
                "select device_id,point,heading,velocity,altitude,seen,message,source_device_type,raw from tracking_loggedpoint where device_id = {} order by seen desc limit 1".format(
                    device_id
                )
            )
            (
                device_id,
                point,
                heading,
                velocity,
                altitude,
                seen,
                message,
                source_device_type,
                raw,
            ) = cursor.fetchone()
            device = Device(
                id=device_id,
                point=point,
                heading=heading,
                velocity=velocity,
                altitude=altitude,
                seen=seen,
                message=message,
                source_device_type=source_device_type,
                deleted=True,
            )
            if source_device_type == "tracplus":
                recreate_tracplus_device_from_raw(device, raw)
            elif source_device_type == "iriditrak":
                recreate_sbd_device_from_raw(device, raw)
            elif source_device_type == "dplus":
                recreate_sbd_device_from_raw(device, raw)
            elif source_device_type == "spot":
                recreate_sbd_device_from_raw(device, raw)
            elif source_device_type == "dfes":
                recreate_dfes_device_from_raw(device, raw)
            elif source_device_type == "mp70":
                recreate_sbd_device_from_raw(device, raw)
            elif source_device_type == "fleetcare":
                recreate_fleetcare_device_from_raw(device, raw)
            elif source_device_type == "fleetcare_error":
                device.source_device_type = "fleetcare"
                recreate_fleetcare_device_from_raw(device, raw)
            else:
                print("Source device type({}) Not Support".format(source_device_type))
                continue
            try:
                with transaction.atomic():
                    device.save()
                recreated_devices.append(device)
            except Exception as ex:
                new_device = Device.objects.filter(deviceid=device.deviceid).first()
                if new_device:
                    # new device object is created for the same resource.
                    cursor.execute(
                        "update tracking_loggedpoint set device_id={1} where device_id={0};".format(
                            device.id, new_device.id
                        )
                    )
                    connection.commit()
                    update_devices.append((device, new_device))
                else:
                    failed_devices.append((device, str(ex)))

        if recreated_devices:
            for device in recreated_devices:
                print(
                    "Recreate device:{}".format(
                        " , ".join(
                            "{}={}".format(column, getattr(device, column))
                            for column in (
                                "id",
                                "deviceid",
                                "source_device_type",
                                "callsign",
                                "callsign_display",
                                "registration",
                                "internal_only",
                                "symbol",
                                "point",
                                "heading",
                                "velocity",
                                "altitude",
                                "seen",
                                "message",
                                "hidden",
                                "deleted",
                            )
                        )
                    )
                )

        if update_devices:
            for device, new_device in update_devices:
                print(
                    "Replace the device({}) with device({}) in table tracking_loggedpoint".format(
                        device.id, new_device.id
                    )
                )

        if failed_devices:
            failed_devices.sort(key=lambda o: o[1].id if o[1] else o[0].id)
            print("\n===============================================================")
            print("Failed to create {} devices".format(len(failed_devices)))
            for device, msg in failed_devices:
                print(
                    "Failed to recreate device:{}".format(
                        " , ".join(
                            "{}={}".format(column, getattr(device, column))
                            for column in (
                                "id",
                                "deviceid",
                                "source_device_type",
                                "callsign",
                                "callsign_display",
                                "registration",
                                "internal_only",
                                "symbol",
                                "point",
                                "heading",
                                "velocity",
                                "altitude",
                                "seen",
                                "message",
                                "hidden",
                                "deleted",
                            )
                        )
                    )
                )
                print("\t{}".format(msg))
                print(
                    "-----------------------------------------------------------------"
                )


def parse_fleetcare_data_from_raw(raw, basetime=timezone.now()):

    data = json.loads(raw)

    # try to parse the timestamp string to datetime object.
    # the format of the timestamp should be 'dd/mm/yyyy HH:MM:SS AM/PM', but sometimes , it can also be 'mm/dd/yyyy HH:MM:SS AM/PM',
    # to handle this issue, the following logic try to parse the datetime with two patterns, and choose the datatime which is close to basetime
    # if the choosed pattern is not the prefered one, will insert a row into table 'tracking_loggedpoint_suspicious'
    # if can't parse the timestamp with all possible patterns, set the source device type to 'fleetcare_error', and also insert a row into table 'tracking_loggepoint_suspicious'
    index = 0
    diff = None
    min_diff = None
    dt = None
    seen = None
    basetime = basetime or timezone.now()

    while index < len(fleetcare_dt_patterns):
        try:
            dt = timezone.make_aware(
                datetime.strptime(data["timestamp"], fleetcare_dt_patterns[index])
            )
            if not seen:
                seen = dt
                min_diff = seen - basetime if seen >= basetime else basetime - seen
                if min_diff <= fleetcare_max_blob_creation_delay:
                    break
            else:
                diff = dt - basetime if dt >= basetime else basetime - dt
                if diff < min_diff:
                    min_diff = diff
                    seen = dt
                    if min_diff <= fleetcare_max_blob_creation_delay:
                        break
        except:
            pass
        finally:
            index += 1

    result = {
        "point": "POINT ({} {})".format(*data["GPS"]["coordinates"]),
        "velocity": int(float(data["readings"]["vehicleSpeed"]) * 1000),
        "altitude": int(float(data["readings"]["vehicleAltitude"])),
        "heading": int(float(data["readings"]["vehicleHeading"])),
    }
    if seen:
        result["seen"] = seen

    return result


def parse_tracplus_data_from_raw(raw):
    data = json.loads(raw)
    return {
        "velocity": int(data["Speed"]) * 1000,
        "altitude": data["Altitude"],
        "heading": data["Track"],
        "seen": timezone.make_aware(
            datetime.strptime(data["Transmitted"], "%Y-%m-%d %H:%M:%S"),
            pytz.timezone("UTC"),
        ),
        "point": "POINT ({} {})".format(data["Longitude"], data["Latitude"]),
    }


def parse_sbd_data_from_raw(raw):
    sbd = json.loads(raw)
    return {
        "point": "POINT({LG} {LT})".format(**sbd),
        "seen": timezone.make_aware(
            datetime.fromtimestamp(float(sbd["TU"])), pytz.timezone("UTC")
        ),
        "heading": abs(sbd.get("DR", 0)),
        "velocity": abs(sbd.get("VL", 0)),
        "altitude": int(sbd.get("AL", 0)),
    }


def parse_dfes_data_from_raw(device, raw):
    data = json.loads(raw)
    prop = data["properties"]
    return {
        "velocity": int(prop["Speed"]) * 1000,
        "heading": prop["Direction"],
        "seen": timezone.make_aware(
            datetime.strptime(prop["Time"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            pytz.timezone("UTC"),
        ),
        "point": "POINT ({} {})".format(
            data["geometry"]["coordinates"][0], data["geometry"]["coordinates"][1]
        ),
    }


def update_loggedpoint_from_raw(
    table="tracking_loggedpoint",
    source_device_types=None,
    batch=3000,
    update=False,
    max_process_rows=999999999,
    min_rowid=None,
    max_rowid=None,
    basetimes=None,
):
    """
    basetimes used by fleetcare to fix datetime format issue, it is a list of tuple( (min id,max id),basetime)
    """
    failed_rows = []

    processed_max_rowid = min_rowid
    processed_rows = 0
    changed_dates = set()
    update_sql_file = "./update_{}.sql".format(table)
    update_log_file = "./update_{}.log".format(table)
    changed_dates_file = "./changed_dates_{}.txt".format(table)

    f_update_sql = open(update_sql_file, "w")
    f_update_log = open(update_log_file, "w")

    if basetimes:
        basetimes.sort(key=lambda o: o[0][0] or 0)
        for o in basetimes:
            if not isinstance(o[1], datetime):
                o[1] = timezone.make_aware(datetime.strptime(o[1], "%Y-%m-%d %H:%M:%S"))
            elif timezone.is_naive(o[1]):
                o[1] = timezone.make_aware(o[1])
            else:
                o[1] = timezone.localtime(o[1])
        print("basetimes = {}".format(basetimes))

    basetime_index = 0

    try:
        with connection.cursor() as cursor:
            while processed_rows < max_process_rows:
                limit = batch
                if source_device_types and processed_max_rowid:
                    if isinstance(source_device_types, (list, tuple)):
                        querysql = "select id,source_device_type,seen,point,heading,altitude,velocity,raw from {0} where id > {1} AND source_device_type in ({2}) order by id asc limit {3};".format(
                            table,
                            processed_max_rowid,
                            ",".join("'{}'".format(t) for t in source_device_types),
                            limit,
                        )
                    else:
                        querysql = "select id,source_device_type,seen,point,heading,altitude,velocity,raw from {0} where id > {1} AND source_device_type = '{2}' order by id asc limit {3};".format(
                            table, processed_max_rowid, source_device_types, limit
                        )
                elif source_device_types:
                    if isinstance(source_device_types, (list, tuple)):
                        querysql = "select id,source_device_type,seen,point,heading,altitude,velocity,raw from {0} where source_device_type in ({1}) order by id asc limit {2};".format(
                            table,
                            ",".join("'{}'".format(t) for t in source_device_types),
                            limit,
                        )
                    else:
                        querysql = "select id,source_device_type,seen,point,heading,altitude,velocity,raw from {0} where source_device_type = '{1}' order by id asc limit {2};".format(
                            table, source_device_types, limit
                        )
                elif processed_max_rowid:
                    querysql = "select id,source_device_type,seen,point,heading,altitude,velocity,raw from {0} where id > {1} order by id asc limit {2};".format(
                        table, processed_max_rowid, limit
                    )
                else:
                    querysql = "select id,source_device_type,seen,point,heading,altitude,velocity,raw from {0} order by id asc limit {1};".format(
                        table, limit
                    )
                print("query logged points with sql \r\n\t{}".format(querysql))
                cursor.execute(querysql)
                rows = cursor.fetchall()
                if not rows:
                    # all rows are processed
                    break
                for (
                    rowid,
                    source_device_type,
                    seen,
                    point,
                    heading,
                    altitude,
                    velocity,
                    raw,
                ) in rows:
                    processed_max_rowid = rowid
                    if max_rowid and rowid > max_rowid:
                        break
                    if source_device_type == "tracplus":
                        data = parse_tracplus_data_from_raw(raw)
                    elif source_device_type == "iriditrak":
                        data = parse_sbd_data_from_raw(raw)
                    elif source_device_type == "dplus":
                        data = parse_sbd_data_from_raw(raw)
                    elif source_device_type == "spot":
                        data = parse_sbd_data_from_raw(raw)
                    elif source_device_type == "dfes":
                        data = parse_dfes_data_from_raw(raw)
                    elif source_device_type == "mp70":
                        data = parse_sbd_data_from_raw(raw)
                    elif source_device_type in ("fleetcare", "fleetcare_error"):
                        basetime = None
                        if basetimes:
                            while basetime_index < len(basetimes):
                                if (
                                    not basetimes[basetime_index][0][0]
                                    or rowid >= basetimes[basetime_index][0][0]
                                ) and (
                                    not basetimes[basetime_index][0][1]
                                    or rowid <= basetimes[basetime_index][0][1]
                                ):
                                    basetime = basetimes[basetime_index][1]
                                    break
                                else:
                                    basetime_index += 1

                        data = parse_fleetcare_data_from_raw(raw, basetime=basetime)
                    else:
                        print(
                            "Source device type({}) Not Support".format(
                                source_device_type
                            )
                        )
                        continue
                    changed_columns = []
                    seen = timezone.localtime(seen)
                    for name, value, to_dbvalue in [
                        (
                            "seen",
                            seen,
                            lambda v: "'{}'".format(
                                v.strftime("%Y-%m-%dT%H:%M:%S.%f+08")
                            ),
                        ),
                        (
                            "point",
                            point,
                            lambda v: "ST_PointFromText('{}',4326)".format(v),
                        ),
                        ("heading", heading, lambda v: str(v)),
                        ("altitude", altitude, lambda v: str(v)),
                        ("velocity", velocity, lambda v: str(v)),
                    ]:
                        if name not in data:
                            # not parsed, ignore
                            continue
                        if name == "point":
                            value = GEOSGeometry(value).wkt
                            data["point"] = GEOSGeometry(data["point"]).wkt

                        if data[name] != value:
                            changed_columns.append(
                                (name, data[name], value, to_dbvalue(data[name]))
                            )

                    if not changed_columns:
                        # not data was changed
                        continue
                    if seen:
                        changed_dates.add(timezone.localtime(seen).date())
                    if data.get("seen"):
                        changed_dates.add(timezone.localtime(data.get("seen")).date())

                    update_sql = "UPDATE {0} SET {2} WHERE id={1};--{3}".format(
                        table,
                        rowid,
                        ",".join(
                            "{}={}".format(name, str(db_value))
                            for name, value, old_value, db_value in changed_columns
                        ),
                        ",".join(
                            "{}:{} -> {}".format(name, old_value, value)
                            for name, value, old_value, db_value in changed_columns
                        ),
                    )
                    f_update_sql.write(update_sql)
                    f_update_sql.write("\n")
                    if update:
                        try:
                            cursor.execute(update_sql)
                            connection.commit()
                            f_update_log.write(
                                "updated row: rowid = {0},changed columns = {1}\r\n{3}\r\n\t{2}\n\n".format(
                                    rowid, changed_columns, update_sql, raw
                                )
                            )
                        except Exception as ex:
                            failed_rows.append(
                                (rowid, changed_columns, update_sql, raw, str(ex))
                            )
                    else:
                        f_update_log.write(
                            "found row: rowid = {0}, changed columns = {1}\r\n{3}\r\n\t{2}\n\n".format(
                                rowid, changed_columns, update_sql, raw
                            )
                        )

                    processed_rows += 1
                    if processed_rows >= max_process_rows:
                        break

                if max_rowid and processed_max_rowid > max_rowid:
                    break

        if failed_rows:
            f_update_log.write(
                "\n=====================================================\n"
            )
            f_update_log.write("Failed to process {} rows\n".format(len(failed_rows)))
            for rowid, changed_columns, update_sql, raw, message in failed_rows:
                f_update_log.write(
                    "rowid = {0}, changed columns = {1}, message={4}\r\n{3}\r\n\t{2}\n".format(
                        rowid, changed_columns, update_sql, raw, message
                    )
                )

    finally:
        with open(changed_dates_file, "a") as f:
            date_list = list(changed_dates)
            date_list.sort()
            for d in date_list:
                f.write(d.strftime("%Y-%m-%d"))
                f.write("\n")
        f_update_sql.close()
        f_update_log.close()
