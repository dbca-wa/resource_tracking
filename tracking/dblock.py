import socket
import os
from datetime import datetime
import random
import string

from django.db import connections,connection
from django.utils import timezone

from . import dbutils

hostname = socket.gethostname()

locker = "{}: {}.{}({})".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),hostname,os.getpid(),''.join(random.choices(string.ascii_uppercase + string.digits, k=10)))

lock_table = "tasklock"
create_lock_table_sql = """
CREATE TABLE IF NOT EXISTS {0} (
  name varchar(64) NOT NULL PRIMARY KEY,
  locker varchar(512) NOT NULL,
  lock_time timestamp with time zone NOT NULL,
  release_time timestamp with timezone
);
""".format(lock_table)

get_lock_sql = """
SELECT locker,lock_time,release_time FROM {0} WHERE name = '{{}}';
""".format(lock_table)

create_lock_sql = """
INSERT INTO {0} 
  (name,locker,lock_time,release_time)
VALUES
  ('{{0}}','{1}','{{1}}',null);
""".format(lock_table,locker)

acquire_lock_sql = """
UPDATE {0} 
SET locker = '{1}', lock_time = '{{1}}', release_time = null
WHERE name = '{{0}}' and locker = '{{2}}' and lock_time = '{{3}}' and release_time = '{{4}}'
""".format(lock_table,locker)

release_lock_sql = """
UPDATE {0} 
SET release_time = '{{1}}'
WHERE name = '{{0}}' and locker = '{1}' and lock_time = '{{2}}'
""".format(lock_table,locker)


dbutils.create_table(connection,"public",lock_table,create_lock_table_sql)

def acquire_lock(name,log=False):
    """
    Return lock time if successfully acquire the lock;otherwise return None
    """
    dbutils.create_table(connection,"public",lock_table,create_lock_table_sql)

    record = dbutils.get(connection,get_lock_sql.format(name))
    if not record:
        try:
            lock_time = timezone.now()
            dbutils.execute(connection,create_lock_sql.format(name,lock_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
            if log:
                print("{0} successfully gets the lock of {1}.".format(locker,name))
            return lock_time
        except Exception as ex:
            #create lock failed, maybe other process already get the lock
            record = dbutils.get(connection,get_lock_sql.format(name))
            if not record:
                #no one acquire the lock. rethrow the exception
                raise ex

    if record[2]:
        #already released, get the lock

        lock_time = timezone.now()
        rows = dbutils.execute(connection,acquire_lock_sql.format(name,lock_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),record[0],record[1].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),record[2].strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        if rows == 1:
            if log:
                print("{0} successfully gets the lock of {1}.".format(locker,name))
            return lock_time
        else:
            if log:
                record = dbutils.get(connection,get_lock_sql.format(name))
                if record:
                    print("{0} can't get the lock of {1}, because {2} already gets the lock at {3}".format(locker,name,record[0],record[1].format('%Y-%m-%d %H:%M:%S.%f')))
                else:
                    raise Exception("{0} is failed to get the lock of {1}".format(locker,name))
            return None

def release(name,lock_time):
    release_time = timezone.now()
    rows = dbutils.execute(connection,release_lock_sql.format(name,release_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),lock_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
    if rows == 1:
        print("{0} successfully releases the lock of {1} at {2}".format(locker,name,release_time.strftime('%Y-%m-%d %H:%M:%S.%f')))
    else:
        record = dbutils.get(connection,get_lock_sql.format(name))
        if not record:
            print("Can't find the lock. the lock is acquired by anyone")
        else:
            if record.release_time:
                raise Exception("{0} is failed to release the lock of {1} which is acquired at {2} because the lock is hold by {3} at {4} and released at {5}".format(
                    locker,
                    name,
                    lock_time,
                    record[0],
                    record[1].strftime('%Y-%m-%d %H:%M:%S.%f'),
                    record[2].strftime('%Y-%m-%d %H:%M:%S.%f')
                ))
       

            else:
                raise Exception("{0} is failed to release the lock of {1} which is acquired at {2} because the lock is currently hold by {3} at {4}".format(
                    locker,
                    name,
                    lock_time,
                    record[0],
                    record[1].strftime('%Y-%m-%d %H:%M:%S.%f'),
                ))
       
