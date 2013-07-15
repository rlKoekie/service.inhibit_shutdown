#!/usr/bin/python
from __future__ import print_function

import xbmc
import xbmcaddon
import subprocess
import re

def port_set(string):
    ret = set()
    for port in re.findall("[0-9]+", string):
        try:
            port = int(port)
        except ValueError:
            continue
        ret.add(port)
    return ret

def log(msg):
    print("{}: {}".format(addon.getAddonInfo('id'), msg))

def check_services(watchlocal, watchremote):
    """ Check if any of the watched services is running. """

    netstat = subprocess.check_output(['/bin/netstat', '-t', '-n'], universal_newlines=True)

    for line in netstat.split('\n')[2:]:
        items = line.split()
        if len(items) < 4: continue
        if not ("udp" in items[0] or "tcp" in items[0] or "raw" in items[0]): continue

        local_addr, local_port = items[3].rsplit(':', 1)
        remote_addr, remote_port = items[4].rsplit(':', 1)

        if local_addr[0] == '[' and local_addr[-1] == ']':
            local_addr = local_addr[1:-1]

        if remote_addr[0] == '[' and remote_addr[-1] == ']':
            remote_addr = remote_addr[1:-1]

        local_port = int(local_port)

        if ((local_addr != remote_addr) and (local_port in watchremote)) or \
            ((local_addr == remote_addr) and (local_port in watclocal)):
            log("Found connection from {} to {}:{}".format(remote_addr, local_addr, local_port))
            return True

    log("No connection found.")
    return False


addon = xbmcaddon.Addon()
s = addon.getSetting
try:
    sleep_time = int(float(s('sleep')) * 1000)
except ValueError:
    sleep_time = 60 * 1000
watched_local = port_set(s('localports'))
watched_remote = port_set(s('remoteports'))
# useless double conversion here, but prevents slightly against idiot input
counterdefault = int(float(s('idlecount')))
counter = counterdefault

log("Watching for remote connections to ports {} and for local connections to ports {}, sleep time is {:0.2f} s.".format(
    ', '.join(str(x) for x in watched_remote),
    ', '.join(str(x) for x in watched_local),
    sleep_time / 1000.0))

while not xbmc.abortRequested:
    if check_services(watched_local, watched_remote):
        xbmc.executebuiltin('InhibitIdleShutdown(true)')
        counter = counterdefault
    elif counter > 0: # if we have a value on the counter, we leave shutdown as it is.
        counter = counter -1
        log("Delay counter is: %i. Not changing InhibitIdleShutdown.")
    else:
        log("Setting InhibitIdleShutdown to false")
        xbmc.executebuiltin('InhibitIdleShutdown(false)')
    xbmc.sleep(sleep_time)
