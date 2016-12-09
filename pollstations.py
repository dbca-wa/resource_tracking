#!/usr/bin/python
from datetime import datetime
from fcntl import fcntl, F_GETFL, F_SETFL
import logging
from logging import handlers
from os import O_NONBLOCK
import re
import subprocess
import time
from subprocess import PIPE, STDOUT

"""
Standalone daemon meant to be run to poll weather stations in parallel.
Example to run using uwsgi:

    attach-daemon2  = exec=venv/bin/python pollstations.py

Should be run from dir with venv and manage.py available.
"""

# Ensure that the logs dir is present.
subprocess.call(['mkdir', '-p', 'logs'])
# Set up logging in a standardised way.
logger = logging.getLogger('pollstations')
logger.setLevel(logging.INFO)
fh = handlers.RotatingFileHandler(
    'logs/pollstations.log', maxBytes=5 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


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
    try:
        station_string = subprocess.check_output(
            ['venv/bin/python', 'manage.py', 'station_metadata'], stderr=STDOUT)
    except subprocess.CalledProcessError as e:
        logger.error(e.output)
        return False
    stations = {}
    # Generate a dict of station IP, port, interval, last polled and process.
    for i in [s for s in station_string.strip().split(",")]:
        if i:
            station = i.split(':')
            stations[station[0]] = {
                'port': station[1],
                'interval': int(station[2]),
                'polled': None,
                'process': None,
                'process_start': None
            }
    return stations


def connect_station(ip, port):
    """Connect to a weather station via Telnet using subprocess, in a
    non-blocking manner.
    """
    logger.info("Connecting to station {}:{}".format(ip, port))
    p = subprocess.Popen(["/usr/bin/telnet", ip, port], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    flags = fcntl(p.stdout, F_GETFL)
    fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
    return p


# Get the dict of weather stations.
try:
    STATIONS = get_stations()
    if STATIONS:
        polling = True
    else:
        polling = False  # No active weather stations.
except subprocess.CalledProcessError as e:
    # We can't do anything without this dict, so abort.
    polling = False

# Observation string patterns
OBS_PATTERNS = [
    '([A-Z]+=\d*\.?\d*\|)',  # Telvent
    '(^0R0),([A-Za-z]{2}=\d+[A-Z])',  # Vaisala
]


while polling:
    # For each station, instantiate a process to poll it for observation data
    # at defined intervals (in minutes).
    # We check to see if the required polling interval has passed and if so, we
    # create a process to poll the station immediately for an observation.
    for ip, metadata in STATIONS.iteritems():
        port = metadata['port']
        process = metadata['process']
        started = metadata['process_start']
        interval = metadata['interval']
        last_poll = metadata['polled']
        now = datetime.now()
        # If the polling interval has passed, create a process and read data.
        if not last_poll or interval <= 1 or ((now - last_poll).total_seconds() / 60) >= interval:
            # No existing process/terminated process: create one now.
            if not process or process.poll() is not None:  # Non-existent/terminated.
                # Establish a connection.
                STATIONS[ip]['process'] = process = connect_station(ip, port)
                STATIONS[ip]['process_start'] = datetime.now()
            try:
                # Read up to 2kb of the connection output and parse the
                # observation string from that.
                data = process.stdout.read(2048)
                # Split the lines of the response and find the observation.
                for line in data.strip().split('\n'):
                    line = line.strip()
                    for pattern in OBS_PATTERNS:
                        if re.search(pattern, line):  # Found matching pattern.
                            STATIONS[ip]['polled'] = datetime.now()
                            # Looks like an observation string; save it.
                            obs = '{}::{}'.format(ip, line)
                            logger.info('Observation data: {}'.format(obs))
                            # This mgmt command will write the observation to the
                            # database and optionally upload it to DAFWA.
                            try:
                                output = subprocess.check_output([
                                    'venv/bin/python', 'manage.py', 'write_observation', obs], stderr=STDOUT)
                                logger.info(output.strip())
                            except subprocess.CalledProcessError as e:
                                logger.error(e.output)
                            # Terminate this polling process if >1 minute, it's finished with.
                            if interval > 1:
                                age = (now - started).total_seconds()
                                logger.info('IP {} poller PID {} killed at {} seconds old'.format(ip, process.pid, age))
                                process.kill()
            except Exception as e:
                continue
    # Pause, and repeat the polling loop.
    time.sleep(3)
