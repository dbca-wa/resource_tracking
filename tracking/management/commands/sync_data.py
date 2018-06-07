import os
import json
import time
from datetime import datetime
import pytz
import traceback

from confy import database

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections,connection
from django.db.models import Q

from tracking.models import Device,LoggedPoint


settings.DATABASES["source_database"] = database.config(name="SOURCE_DATABASE_URL")

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sync_status (
  tablename varchar(64) NOT NULL PRIMARY KEY,
  pid integer NOT NULL,
  syncing boolean NOT NULL DEFAULT FALSE,
  start_time timestamp with time zone NOT NULL,
  end_time timestamp with time zone,
  last_sync_id varchar(256),
  synced_rows integer
)
"""

GET_LOCK_SQL = """
INSERT INTO sync_status AS a
    (tablename,pid,syncing,start_time,end_time,last_sync_id,synced_rows)
VALUES
    ('{0}',{1},TRUE,current_timestamp,null,null,null)
ON CONFLICT(tablename) DO UPDATE SET pid = {1}, syncing = TRUE,start_time = current_timestamp,end_time = null,synced_rows = null
    WHERE a.tablename = '{0}' AND not a.syncing
"""

UPDATE_SYNC_SQL = """
UPDATE sync_status SET last_sync_id = '{2}', synced_rows = {3}
    WHERE tablename = '{0}' AND pid = {1}
"""

END_SYNC_SQL = """
UPDATE sync_status SET end_time = current_timestamp,syncing = FALSE
    WHERE tablename = '{0}' AND pid = {1}
"""

READONLY_COLUMNS = {
    "tracplus" : [],
    "iriditrak":["callsign","model","registration"],
    "dplus":["callsign","model","registration"],
    "spot":["callsign","model","registration"],
    "dfes":[],
    "other":["callsign","model","registration"]
}

SYNC_DEVICE_COLUMNS = ["deviceid","source_device_type","callsign","registration","velocity","altitude","heading","seen","point","message"]
READ_DEVICE_SQL = """
    SELECT {}
""".format(",".join(SYNC_DEVICE_COLUMNS)) + ",(seen <= now()) as is_valid" + """
    FROM tracking_device 
    ORDER BY seen,deviceid
    LIMIT {0}
"""

READ_DEVICE_WITH_CONDITION_SQL = """
    SELECT {}
""".format(",".join(SYNC_DEVICE_COLUMNS)) + ",(seen <= now()) as is_valid" + """
    FROM tracking_device 
    WHERE seen > '{seen}' OR (seen = '{seen}' AND deviceid > '{deviceid}')
    ORDER BY seen,deviceid
    LIMIT {0}
"""

SYNC_LOGGEDPOINT_COLUMNS = ["source_device_type","point","heading","velocity","altitude","seen","message","raw"]
READ_LOGGEDPOINT_SQL = """
    SELECT {}
""".format(",".join(["a.{}".format(col) for col in SYNC_LOGGEDPOINT_COLUMNS])) + ",a.id,b.deviceid,(a.seen <= now()) as is_valid"  + """
    FROM tracking_loggedpoint a join tracking_device b on a.device_id = b.id
    ORDER BY a.id
    LIMIT {0}
"""

READ_LOGGEDPOINT_WITH_CONDITION_SQL = """
    SELECT {}
""".format(",".join(["a.{}".format(col) for col in SYNC_LOGGEDPOINT_COLUMNS])) + ",a.id,b.deviceid,(a.seen <= now()) as is_valid"  + """
    FROM tracking_loggedpoint a join tracking_device b on a.device_id = b.id
    WHERE a.id > {id}
    ORDER BY a.id
    LIMIT {0}
"""
PERTH_TZ = pytz.timezone("Australia/Perth")

def json_serial(obj):
   if isinstance(obj,datetime):
       #d = obj.astimezone(PERTH_TZ)
       #return [d.year,d.month,d.day,d.hour,d.minute,d.second,d.microsecond]
       d = obj.astimezone(pytz.UTC)
       return d.strftime("%Y-%m-%d %H:%M:%S.%f+00")

devices = {}

class Command(BaseCommand):
    help = "Synchronize device and history data from other resource tracking database"

    def syncDevice(self,tablename,cond):
        cond = cond or {}
        loaded_object = {}
        insert_rows = 0
        update_rows = 0
        invalid_rows = 0
        deviceid = None
        last_sync_sql = None
        try:
            while True:
                max_reading_rows = 100
                if cond:
                    last_sync_sql = READ_DEVICE_WITH_CONDITION_SQL.format(max_reading_rows,**cond)
                else:
                    last_sync_sql = READ_DEVICE_SQL.format(max_reading_rows)
                with connections["source_database"].cursor() as cursor:
                    cursor.execute(last_sync_sql)
                    rows = cursor.fetchall()
                for row in rows:
                    index = 0
                    loaded_object.clear()
                    for column in SYNC_DEVICE_COLUMNS:
                        if column == "deviceid":
                            deviceid = row[index]
                        elif "source_device_type" not in loaded_object:
                            loaded_object[column] = row[index]
                        elif column not in (READONLY_COLUMNS.get(loaded_object["source_device_type"].lower()) or []):
                            loaded_object[column] = row[index]
                        index += 1
    
                    is_valid = row[index]
                    index += 1
                    if not is_valid:
                        invalid_rows += 1
                        continue;
                    device ,created = Device.objects.update_or_create(deviceid=deviceid,defaults=loaded_object)
                    cond["deviceid"] = deviceid
                    cond["seen"] = loaded_object["seen"]
                    devices[deviceid] = device
                    if created:
                        insert_rows += 1
                        #print "insert device {}".format(deviceid)
                    else:
                        update_rows += 1
                        #print "update device {}".format(deviceid)
                #print "{} : synchronized {} rows (insert {} rows, update {} rows)".format(tablename,(insert_rows + update_rows),insert_rows,update_rows)
                if invalid_rows:
                    cond["invalid_rows"] = invalid_rows
                elif "invalid_rows" in cond:
                    del cond["invalid_rows"]

                with connection.cursor() as cursor:
                    cursor.execute(UPDATE_SYNC_SQL.format(tablename,self.pid,json.dumps(cond,default=json_serial),(insert_rows + update_rows)))

                if len(rows) < max_reading_rows:
                    break
                else:
                    time.sleep(0.1)
        except:
            print "{} : Failed,deviceid={}! synchronized {} rows (insert {} rows, update {} rows)".format(tablename,deviceid,(insert_rows + update_rows),insert_rows,update_rows)
            traceback.print_exc()
            with connection.cursor() as cursor:
                cursor.execute(UPDATE_SYNC_SQL.format(tablename,self.pid,json.dumps(cond,default=json_serial),(insert_rows + update_rows)))

    def syncLoggedPoint(self,tablename,cond):
        remain_rows = self.limit if self.limit > 0 else -1
        cond = cond or {}
        loaded_object = {}
        insert_rows = 0
        ignored_rows = 0
        invalid_rows = 0
        last_sync_sql = None
        try:
            while True:
                max_reading_rows = remain_rows if remain_rows < 100 else 100
                if cond:
                    last_sync_sql = READ_LOGGEDPOINT_WITH_CONDITION_SQL.format(max_reading_rows,**cond)
                else:
                    last_sync_sql = READ_LOGGEDPOINT_SQL.format(max_reading_rows)
                with connections["source_database"].cursor() as cursor:
                    cursor.execute(last_sync_sql)
                    rows = cursor.fetchall()
                for row in rows:
                    index = 0
                    for column in SYNC_LOGGEDPOINT_COLUMNS:
                        loaded_object[column] = row[index]
                        index += 1
    
                    rowid = row[index]
                    index += 1
                    deviceid = row[index]
                    index += 1
                    is_valid = row[index]
                    index += 1
                    if not is_valid:
                        invalid_rows = 0
                        continue;
                    try:
                        if deviceid not in devices:
                            devices[deviceid] = Device.objects.get(deviceid = deviceid)
                            
                        device = devices[deviceid]
                    except:
                        #print "Device {} Not Found".format(deviceid)
                        ignored_rows += 1
                        continue
    
                    obj,created = LoggedPoint.objects.get_or_create(device=device,seen=loaded_object["seen"],defaults=loaded_object)
                    cond["id"] = rowid
                    cond["deviceid"] = deviceid
                    cond["seen"]=loaded_object["seen"]
                    if created:
                        insert_rows += 1
    
                if invalid_rows:
                    cond["invalid_rows"] = invalid_rows
                elif "invalid_rows" in cond:
                    del cond["invalid_rows"]
                if ignored_rows:
                    cond["ignored_rows"] = ignored_rows
                elif "ignored_rows" in cond:
                    del cond["ignored_rows"]
                #print "{} : synchronized {} rows (insert {} rows, ignored {} rows)".format(tablename,(insert_rows + ignored_rows),insert_rows,ignored_rows)
                with connection.cursor() as cursor:
                    cursor.execute(UPDATE_SYNC_SQL.format(tablename,self.pid,json.dumps(cond,default=json_serial),(insert_rows)))

                if len(rows) < max_reading_rows:
                    break
                else:
                    time.sleep(0.1)
        except:
            #print "{} : Failed! synchronized {} rows (insert {} rows, ignored {} rows)".format(tablename,(insert_rows + ignored_rows),insert_rows,ignored_rows)
            traceback.print_exc()
            with connection.cursor() as cursor:
                cursor.execute(UPDATE_SYNC_SQL.format(tablename,self.pid,json.dumps(cond,default=json_serial),(insert_rows + ignored_rows) ))
                

    def handle(self, *args, **options):
        self.pid = os.getpid()
        self.limit = 100
	
        try:
            with connection.cursor() as cursor:
                #create sync_status table if not exist
                cursor.execute(TABLE_SQL)

            for m in (Device,LoggedPoint):
                tablename = m._meta.model_name
                with connection.cursor() as cursor:
                    #try to get the lock to sync
                    cursor.execute(GET_LOCK_SQL.format(tablename,self.pid))
                    cursor.execute("SELECT last_sync_id FROM sync_status WHERE tablename='{}' and pid={}".format(tablename,self.pid))
                    row = cursor.fetchone()
                if not row:
                    #can't get the lock to sync device
                    continue
                try:
                    cond = json.loads(row[0]) if row[0] else None
                    if tablename == "device":
                        self.syncDevice(tablename,cond)
                    else:
                        self.syncLoggedPoint(tablename,cond)
                        pass
                finally:
                    with connection.cursor() as cursor:
                        cursor.execute(END_SYNC_SQL.format(tablename,self.pid ))
                
        except Exception as e:
            traceback.print_exc()

