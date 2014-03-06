#!/usr/bin/python
from __future__ import print_function

import xbmc
import xbmcaddon
import subprocess
import re
from os import path, popen
global sleep_time, watched_local, watched_remote, counterdefault, addon
global lockfilepaths, transmisionMinimalSpeed , transmissionCmd, debugMe

class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
    def onSettingsChanged( self ):
        load_settings()

def port_set(string):
    ret = set()
    for port in re.findall("[0-9]+", string):
        try:
            port = int(port)
        except ValueError:
            continue
        ret.add(port)
    return ret

def mylog(msg):
    if debugMe:
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
            ((local_addr == remote_addr) and (local_port in watchlocal)):
            mylog("Found connection from {} to {}:{}".format(remote_addr, local_addr, local_port))
            return True

    mylog("No connection found.")
    return False

def check_lockfiles(lockfilelist=[]):
    for i in lockfilelist:
        if path.exists(i):
            mylog("lockfile(s) found: %s" %(i))
            return True
    return False

# function to check the status of transmission. if running, it checks if the downloads are going fast enough to keep the system awake
def check_transmission(transmissioncommand,transmissionminimalspeed=10.0):
    try: transmissioninfo = popen(transmissioncommand).read()
    except:
        mylog("transmission-remote error. is transmission-remote installed on this system?")
        return False
    else: 
        if transmissioninfo == '':
            mylog("transmission not running or not giving any response")
            return False
        elif float(transmissioninfo.split()[-1]) >= transmissionminimalspeed:
            mylog("transmission downloading: %s kb/s" %(transmissioninfo.split()[-1]))
            return True
        else:
            mylog("transmission downloading too slow: %s kb/s" %(transmissioninfo.split()[-1]))
            return False
    return False

def check_all(watchlocal=set(), watchremote=set(), lockfilelist=[], transmissioncommand="", transmissionminimalspeed=0.0):
    # this routine checks if the system is active. If it finds an activity, it will return True and not check other activities.
    if lockfilelist:
        if check_lockfiles(lockfilelist):
            return True
    if watchlocal or watchremote:
        if check_services(watchlocal,watchremote):
            return True
    if transmissioncommand:
        if check_transmission(transmissioncommand, transmissionminimalspeed):
            return True
    return False

def load_settings():
    global sleep_time, watched_local, watched_remote, counterdefault, addon
    global lockfilepaths, transmisionMinimalSpeed , transmissionCmd, debugMe
    
    addon = xbmcaddon.Addon()
    s = addon.getSetting
    try:
        sleep_time = int(s('sleep'))
    except ValueError:
        sleep_time = 60
    watched_local = port_set(s('localports'))
    watched_remote = port_set(s('remoteports'))
    counterdefault = int(s('idlecount'))
    lockfilepaths=s('lockfilepaths')
    if lockfilepaths:
        lockfilepaths=lockfilepaths.split(";")
    else:
        lockfilepaths=[]
    checkTransmission = s('checktransmission') == 'true'
    transmisionMinimalSpeed = float(s('transmissionminspeed'))
    transmissionUsername = s('transmissionuser')
    transmissionPasswd = s('transmissionpass')
    if not checkTransmission:
        transmissionCmd = ""
    elif transmissionUsername and transmissionPasswd:
        transmissionCmd = "transmission-remote -n %s:%s -l" %(transmissionUsername, transmissionPasswd)
    else:
        transmissionCmd = "transmission-remote -l"
    debugMe = s('debugme') == 'true'
    #FIXME: I need to check if transmission-remote always returns kb/s

load_settings()
counter = counterdefault

mylog("Watching for remote connections to ports {} and for local connections to ports {}, sleep time is {} s.".format(
    ', '.join(str(x) for x in watched_remote),
    ', '.join(str(x) for x in watched_local),
    sleep_time))

while not xbmc.abortRequested:
    for i in range(sleep_time):
        if xbmc.abortRequested: break
        load_settings()
        if i==0:
            if check_all(watched_local, watched_remote, lockfilepaths, transmissionCmd, transmisionMinimalSpeed):
                mylog("Setting InhibitIdleShutdown to true")
                xbmc.executebuiltin('InhibitIdleShutdown(true)')
                counter = counterdefault
            elif counter > 0: # if we have a value on the counter, we leave shutdown as it is.
                counter = counter -1
                mylog("Delay counter is: %i. Not changing InhibitIdleShutdown." %(counter))
            else:
                mylog("Setting InhibitIdleShutdown to false")
                xbmc.executebuiltin('InhibitIdleShutdown(false)')
        xbmc.sleep(1000)
