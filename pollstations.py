#!/usr/bin/python
from datetime import datetime
from fcntl import fcntl, F_GETFL, F_SETFL
import logging
from logging import handlers
from os import O_NONBLOCK, kill
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
            if LOGGER:
                LOGGER.info("Killing pid {}".format(pid))
            self.process.terminate()
            if self.process.poll() is None:
            # Check if the process has really terminated & force kill if not.
                self.process.kill()
                self.process.poll()
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


def polling_loop(stations):
    """The main polling loop function.
    """
    loop_count = 0
    if stations:
        polling = True
    else:
        polling = False  # No active weather stations.

    while polling:
        # For each station, instantiate a process to poll it for observation
        # data at defined intervals (in minutes).
        # We check to see if the required polling interval has passed and if so,
        # we create a process to poll the station immediately for an observation.
        for s in stations:
            now = datetime.now()
            # Poll for observation data if:
            # - the station has never been polled;
            # - the interval is <1 minute;
            # - the polling interval (minutes) has passed.
            if s.last_poll is None or s.interval <= 1 or ((now - s.last_poll).total_seconds() / 60) >= s.interval:
                # If no existing process exist or process is terminated, start one now.
                if not s.process or s.process.poll() is not None:  # Non-existent/terminated.
                    # Establish a connection.
                    s.connect_station()
                    s.process_start = datetime.now()
                try:
                    # Read up to 2kb of the connection output and parse the
                    # observation string from that.
                    data = s.process.stdout.read(2048)
                    # Split the lines of the response and find the observation.
                    for line in data.strip().split('\n'):
                        line = line.strip()
                        for pattern in s.patterns:
                            if re.search(pattern, line):  # Found a matching pattern in the output.
                                s.last_poll = datetime.now()
                                # Looks like an observation string; save it.
                                obs = '{}::{}'.format(s.ip, line)
                                if LOGGER:
                                    LOGGER.info('Observation data: {}'.format(obs))

                                # This mgmt command will write the observation to the
                                # database and optionally upload it to DAFWA.
                                try:
                                    output = subprocess.check_output(
                                        ['venv/bin/python', 'manage.py', 'write_observation', obs],
                                        stderr=STDOUT)
                                    if LOGGER:
                                        LOGGER.info(output.strip())
                                except subprocess.CalledProcessError as e:
                                    if LOGGER:
                                        LOGGER.error(e.output)

                                # Terminate the process if interval >1 minute, it's finished with.
                                if s.interval > 1:
                                    if LOGGER:
                                        age = (now - s.process_start).total_seconds()
                                        LOGGER.info('Polling {} process PID {} ended at {} seconds old'.format(
                                            s.ip, s.process.pid, age))
                                    s.terminate_poll_process()
                except Exception as e:
                    # No connection output; set last_poll to false for connection cleanup
                    s.last_poll = False
                    if LOGGER:
                        LOGGER.error(e);

            # If we have an active session but the time since last poll has
            # exceeded the interval by more than two minutes, we may have a
            # stuck telnet session (stays alive but stops sending output).
            # In that event, we'll never get to the call to terminate the
            # process, so let's do so now.
            if s.last_poll is False or (s.last_poll and ((now - s.last_poll).total_seconds() / 60) >= s.interval + 2):
                s.terminate_poll_process()
                s.last_poll = None
                if LOGGER:
                    LOGGER.warning('Polling {} process might be stuck, cleaning up {}'.format(s.ip, s.process.pid))

        # Every ten polling loops, review the list of active weather stations.
        # Compare against the current list of polled stations, and add/remove
        # any stations as required.
        # This step is undertaken so that the polling service doesn't need to
        # be restarted to reset the current list of "active" stations.
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

        # Pause, and repeat the polling loop.
        time.sleep(3)


if __name__ == "__main__":
    LOGGER = configure_logging()
    stations = configure_stations()
    polling_loop(stations)
