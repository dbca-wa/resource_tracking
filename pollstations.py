#!/usr/bin/env python
from fcntl import fcntl, F_GETFL, F_SETFL
from datetime import datetime
from os import O_NONBLOCK
import subprocess
import time


def get_stations():
    """Query the weather app for active AW stations and return a dict of
    station metadata. The dict is used to manage polling processes and the
    interval of polling. Format of the returned dict:

    {
        'IP_ADDRESS': {
            'port': PORT_NUMBER_INT,
            'interval': MINUTES_INT,
            'polled': None,
            'process': None
        },
        ...
    }
    """
    # Parse the list of IPs for active weather stations.
    station_string = subprocess.check_output(
        ['python', 'manage.py', 'station_ips'], stderr=subprocess.STDOUT)
    stations = {}
    # Generate a dict of station IP, port, interval, last polled and process.
    for i in [s for s in station_string.strip().split(",")]:
        station = i.split(':')
        stations[station[0]] = {
            'port': station[1],
            'interval': int(station[2]),
            'polled': None,
            'process': None
        }
    return stations


def connect_station(ip, port):
    """Connect to a weather station via Telnet using subprocess, in a
    non-blocking manner.
    """
    #print("Connecting to station {}:{}".format(ip, port))
    p = subprocess.Popen(["telnet", ip, port], stdout=subprocess.PIPE)
    flags = fcntl(p.stdout, F_GETFL)
    fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
    return p


# Get the dict of weather stations.
try:
    STATIONS = get_stations()
    polling = True
except subprocess.CalledProcessError as e:
    # We can't do anything without this dict, so abort.
    polling = False


while polling:
    # For each station, instantiate a process to poll it for observation data
    # at defined intervals (in minutes).
    # We check to see if the required polling interval has passed and if so, we
    # create a process to poll the station immediately for an observation.
    for ip, metadata in STATIONS.iteritems():
        port = metadata['port']
        process = metadata['process']
        interval = metadata['interval']
        last_poll = metadata['polled']
        now = datetime.now()
        # If the polling interval has passed, create a process and read data.
        if not last_poll or ((now - last_poll).total_seconds() / 60) >= interval:
            # If any existing process hasn't terminated, do so now.
            if not process or process.poll() is not None:  # Non-existent/terminated.
                if process:
                    # Kill process and reconnect if exited
                    try:
                        process.kill()
                    except Exception as e:
                        pass
                # Establish a connection.
                STATIONS[ip]['process'] = process = connect_station(ip, port)
            try:
                # Read up to 2kb of the connection output and parse the
                # observation string from that.
                data = process.stdout.read(2048)
                # Split the lines of the response and find the observation.
                for line in data.strip().split('\n'):
                    line = line.strip()
                    if line.find('=') > -1:  # Hopefully any welcome msg never contains "=" :/
                        STATIONS[ip]['polled'] = datetime.now()
                        # Looks like a weather string; feed to Django
                        process.terminate()
                        obs = '{}::{}'.format(ip, line)
                        # This mgmt command will write the observation to the
                        # db and optionally upload it to DAFWA.
                        subprocess.call(['python', 'manage.py', 'write_observation', obs])
            except Exception as e:
                continue
    # Pause, and repeat the polling loop.
    time.sleep(3)
