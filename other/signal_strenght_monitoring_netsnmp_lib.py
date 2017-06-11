#!/usr/bin/python3
import netsnmp
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
    oid = netsnmp.Varbind('enterprises.32108.2.4.3.3.1.2')
    while True:
        signalStrength = netsnmp.snmpwalk(
            oid, Version=1, DestHost="172.23.104.1", Community="public")
        for i in range(len(signalStrength)):
            if int(signalStrength[i]) > 250:
                time.sleep(60)
                currentSignalStrength = int(signalStrength[i]) / 10
                smsText = "Соколовская 76а: высокий уровень сигнала на анализаторе : {} dBuV".format(
                    currentSignalStrength)
                send_sms(smsText)
                time.sleep(60)
                while True:
                    repeatSignalStrenght = netsnmp.snmpwalk(
                        oid, Version=1, DestHost="172.23.104.1", Community="public")
                    if repeatSignalStrenght[i] < 250:
                        currentSignalStrength = int(signalStrength[i]) / 10
                        smsText = "Соколовская 76а: низкий уровень сигнала на анализаторе : {} dBuV".format(
                            currentSignalStrength[i])
                        send_sms(smsText)
                    break
                    time.sleep(60)
        time.sleep(60)

if __name__ == '__main__':
    daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)
