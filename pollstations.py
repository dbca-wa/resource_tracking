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


class Station:
    """A class to store a weather station's metadata and polling process.
    """
    # Observation string patterns
    patterns = [
        '([A-Z]+=\d*\.?\d*\|)',  # Telvent
        '(^0[Rr]0),([A-Za-z]{2}=-?(\d+(\.\d+)?)[A-Za-z#],?)+',  # Vaisala
    ]

    def __init__(self, ip, port, interval):
        self.ip = str(ip)
        self.port = str(port)
        self.interval = interval
        self.polled = None
        self.process = None
        self.process_start = None
        self.last_poll = None
        self.failures = 0

    def __str__(self):
        return u'{}:{} ({}m)'.format(self.ip, self.port, self.interval)

    def connect_station(self):
        """Connect to a weather station via Telnet using subprocess in a
        non-blocking manner.
        """
        if LOGGER:
            LOGGER.info("Connecting to station {}:{}".format(self.ip, self.port))
        p = subprocess.Popen(
            ["/usr/bin/telnet", self.ip, self.port], stdin=PIPE, stdout=PIPE,
            stderr=PIPE)
        flags = fcntl(p.stdout, F_GETFL)
        fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
        self.process = p

    def terminate_poll_process(self):
        """Function to end a polling process gracefully if possible and
        forcefully if required.
        """
        if self.process:
            # Try to terminate the process gracefully.
            pid = self.process.pid
            self.process.terminate()
            time.sleep(1)
            exitcode = self.process.poll()
            if LOGGER:
                LOGGER.info("Killed pid {} exitcode {}".format(pid, exitcode))
            self.process = None


def configure_logging():
    # Ensure that the logs dir is present.
    subprocess.call(['mkdir', '-p', 'logs'])
    LOGGER = logging.getLogger('pollstations')
    LOGGER.setLevel(logging.INFO)
    fh = handlers.RotatingFileHandler(
        'logs/pollstations.log', maxBytes=5 * 1024 * 1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    LOGGER.addHandler(fh)
    return LOGGER


def configure_stations():
    stations = []
    try:
        # Query the weather app for active AW stations and return a list of
        # Station instances. The list is used to manage polling processes and the
        # interval of polling.
        # Parse the list of IPs for active weather stations. Response is a comma-
        # separated list of IP:PORT:INTERVAL, e.g.:
        # 10.3.15.100:43000:1,10.3.26.254:43000:1,10.3.25.254:43000:1
        station_string = subprocess.check_output(
            ['venv/bin/python', 'manage.py', 'station_metadata'], stderr=STDOUT)
        # Instantiate the list of weather stations.
        for i in [s for s in station_string.strip().split(",")]:
            ip, port, interval = i.split(':')
            stations.append(Station(ip, port, int(interval)))
    except subprocess.CalledProcessError as e:
        # We can't do anything without this list, so abort.
        if LOGGER:
            LOGGER.error(e.output)
        return []
    return stations


def should_poll(station):
    # Poll for observation data if:
    # - the station has never been polled;
    # - the interval is <=1 minute;
    # - the polling interval (minutes) has passed.
    now = datetime.now()
    if not station.last_poll or station.interval <= 1:
        return True
    elif (now - station.last_poll).total_seconds() / 60 >= station.interval:
        return True
    else:
        return False


def polling_loop(stations):
    """The main polling loop function.
    """
    loop_count = 0
    if stations:
        polling = True
    else:
        polling = False  # No active weather stations.

    while polling:
        # Poll max every 3 secs
        time.sleep(3)
        # For each station, instantiate a process to poll it for observation
        # data at defined intervals (in minutes).
        # We check to see if the required polling interval has passed and if so,
        # we create a process to poll the station immediately for an observation.
        for station in stations:
            # If we have an active session but the time since last poll has
            # exceeded the interval by more than two minutes, we may have a
            # stuck telnet session (stays alive but stops sending output).
            # In that event, we'll never get to the call to terminate the
            # process, so let's do so now.
            if station.failures > 2:
                station.last_poll = None
                if LOGGER:
                    LOGGER.warning('Polling {} process failed {} times, killing'.format(station.ip, station.failures))
                station.terminate_poll_process()
                station.failures = 0

            if should_poll(station):
                if not (station.process and station.process.poll() is None): # check for process or exit code
                    # If no existing process exist or process is terminated, start one now.
                    station.connect_station()
                    station.process_start = datetime.now()
                try:
                    # Read up to 2kb of the connection output and parse the
                    # observation string from that.
                    data = station.process.stdout.read(2048)
                except Exception as e:
                    # No connection output; pass and try again next loop.
                    if station.last_poll and (datetime.now() - station.last_poll).total_seconds() / 60 > station.interval + station.failures:
                        # if data late, increment failures
                        station.failures += 1
                        LOGGER.error("No data received from {} for {} seconds".format(station.ip, (datetime.now() - station.last_poll).total_seconds()))
                    continue
                # Split the lines of the response and find the observation.
                for line in data.strip().split('\n'):
                    line = line.strip()
                    for pattern in station.patterns:
                        if re.search(pattern, line):  # Found a matching pattern in the output.
                            station.last_poll = datetime.now()
                            # Looks like an observation string; save it.
                            obs = '{}::{}'.format(station.ip, line)
                            if LOGGER:
                                LOGGER.info('Observation data: {}'.format(obs))
                            # This mgmt command will write the observation to the
                            # database and to the upload_data_cache directory.
                            try:
                                output = subprocess.check_output(
                                    ['venv/bin/python', 'manage.py', 'write_observation', obs],
                                    stderr=STDOUT)
                                station.failures = 0
                                if LOGGER:
                                    LOGGER.info(output.strip())
                            except subprocess.CalledProcessError as e:
                                if LOGGER:
                                    LOGGER.error(e.output)

                            # Terminate the process if interval >1 minute, it's finished with.
                            if station.process and station.interval > 1:
                                if LOGGER:
                                    age = (datetime.now() - station.process_start).total_seconds()
                                    LOGGER.info('Polling {} process PID {} ended at {} seconds old'.format(
                                        station.ip, station.process.pid, age))
                                station.terminate_poll_process()

        # Every ten polling loops, review the list of active weather stations.
        # Compare against the current list of polled stations, and add/remove
        # any stations as required.
        # This step is undertaken so that the polling service doesn't need to
        # be restarted to reset the current list of "active" stations.
        # Also call the management command to upload cached observation data.
        if loop_count == 10:
            stations_update = configure_stations()
            for station in stations_update:
                # If a Station with this IP is not being polled, append it.
                if station.ip not in [s.ip for s in stations]:
                    stations.append(station)
                    if LOGGER:
                        LOGGER.info('{} was added to the station pool'.format(station.ip))
                else:  # Station is currently being polled.
                    cur_station = next(s for s in stations if s.ip == station.ip)
                    # Check/update the station polling interval.
                    if cur_station.interval != station.interval:
                        cur_station.interval = station.interval
                        cur_station.last_poll = None  # Reset.
                        if LOGGER:
                            LOGGER.info('{} polling interval was updated'.format(cur_station.ip))
            # If the currently-polled stations include any that aren't active,
            # remove those from the list.
            for cur_station in list(stations):
                if cur_station.ip not in [s.ip for s in stations_update]:
                    stations.remove(cur_station)
                    if LOGGER:
                        LOGGER.info('{} was removed from the station pool'.format(cur_station.ip))

            # Reset the loop counter.
            loop_count = 0
        else:
            loop_count += 1


if __name__ == "__main__":
    LOGGER = configure_logging()
    stations = configure_stations()
    polling_loop(stations)
