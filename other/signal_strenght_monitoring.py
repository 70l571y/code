#!/usr/bin/python3
from pysnmp.hlapi import *
import time
import urllib.request
import urllib.parse
import os
from daemon import daemon_exec

pathToPID = '/tmp/roman/daemons/'
nameOfPID = 'signal_strenght'
if not os.path.exists(pathToPID):
    os.makedirs(pathToPID)
out = {'stdout': pathToPID + nameOfPID + '.log'}
action = 'start'

def send_sms(text):
    smsText = {"!": text}
    encSMSText = urllib.parse.urlencode(smsText)
    url = "https://sms.ru/sms/send?api_id=CCE170B7-6F1F-1614-EB4F-C987F279B26C&to=79135710835&msg="
    f = urllib.request.urlopen(url + encSMSText)

def main():
    for (errorIndication,
         errorStatus,
         errorIndex,
         varBinds) in nextCmd(SnmpEngine(),
                              CommunityData('public', mpModel=0),
                              UdpTransportTarget(('172.23.104.1', 161)),
                              ContextData(),
                              ObjectType(ObjectIdentity(
                                  'SNMPv2-SMI', 'enterprises', 32108)),
                              lookupMib=False):

        if errorIndication:
            print(errorIndication)
            break
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
            break
        else:
            for varBind in varBinds:
                print(' = '.join([x.prettyPrint() for x in varBind]))



if __name__ == '__main__':
    daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)