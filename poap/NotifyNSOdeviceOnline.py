#!/bin/env python

#import glob
import os
#import pkgutil
import re
#import shutil
#import signal
import sys
import syslog
import time
#from time import gmtime, strftime
#import tarfile
#import errno
import httplib
import base64
import string
import json

#try:
#    import subprocess as sp
#except ImportError:
#    sp = None

try:
    from cisco import cli
    from cisco import transfer
    legacy = True
except ImportError:
    from cli import *
    legacy = False

script_version = ".5"
syslog_prefix = "NSO Event Notification: "
serial_number = None
nso_ip = "10.95.5.60"
nso_port = 8080
nso_username = "admin"
nso_password = "admin"

def nso_request(request_path, operation='GET', payload=''):
    url = "http://" + nso_ip + ":" + str(nso_port) + request_path
    event_log("NSO request: " + url)
    auth = base64.encodestring('%s:%s' % (nso_username, nso_password)).replace('\n', '')
    headers = {"Accept": "application/vnd.yang.data+json", "Content-Type": "application/vnd.yang.data+xml", "Authorization": "Basic %s" % auth}
    conn = httplib.HTTPConnection(host=nso_ip, port=nso_port)
    conn.request(method=operation, url=request_path, body=payload, headers=headers)
    response = conn.getresponse()
    response_data = {'status': response.status}
    if operation == 'GET':
        response_data['data'] = json.loads(response.read())
    conn.close()
    event_log("NSO request status: " + str(response.status) + " : " + response.reason)
    return response_data

def update_device_state_in_nso(serial_number, state):
    request_path = "/api/running/poap"
    payload = """
<poap>
  <device>
    <id>{SERIAL_NUMBER}</id>
    <device-state>{STATE}</device-state>
  </device>
</poap>
    """.format(SERIAL_NUMBER=serial_number, STATE=state)
    return nso_request(request_path, 'PATCH', payload)


def event_log(info):
    """
    Log the trace into console
    Args:
        info: The information that needs to be logged.
    """
    global syslog_prefix

    # Don't syslog passwords
    parts = re.split("\s+", info.strip())
    for (index, part) in enumerate(parts):
        # blank out the password after the password keyword (terminal password *****, etc.)
        if part == "password" and len(parts) >= index+2:
            parts[index+1] = "<removed>"

    # Recombine for syslogging
    info = " ".join(parts)

    # We could potentially get a traceback (and trigger this) before
    # we have called init_globals. Make sure we can still log successfully
    try:
        info = "%s - %s" % (syslog_prefix, info)
    except NameError:
        info = " - %s" % info

    syslog.syslog(9, info)

def main():
    global serial_number

    event_log("Running script version "+script_version)
    serial_number = cli("show version | grep 'Processor Board ID' | cut -d ' ' -f 6").strip()
    event_log("Device Serial Number: " + serial_number)
    counter = 0
    while cli('show interface mgmt 0 brief | grep mgmt0').split()[3] == '--' and counter < 10:
        time.sleep(10)
        counter = counter + 1
    update_device_state_in_nso(serial_number, 'ONLINE')

if __name__ == "__main__":
    try:
        main()
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        event_log("Exception: {0} {1}".format(exc_type, exc_value))
        while exc_tb is not None:
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            event_log("Stack - File: {0} Line: {1}"
                     .format(fname, exc_tb.tb_lineno))
            exc_tb = exc_tb.tb_next
        abort()

