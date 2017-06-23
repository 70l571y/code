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

def snmp_walk():
    oid = netsnmp.Varbind('enterprises.32108.2.4.3.3.1.2')
    signalStrength = netsnmp.snmpwalk(
        oid, Version=1, DestHost="172.23.104.1", Community="public")
    print(time.ctime(), '- сняты показания по SNMP с устройства')
    return signalStrength

def main():
    while True:
        analysisBigSignalStrenght = snmp_walk()
        for i in range(len(analysisBigSignalStrenght)):
            if int(analysisBigSignalStrenght[i]) > 250:
                currentSignalStrength = int(analysisBigSignalStrenght[i]) / 10
                smsText = "Соколовская 76а: высокий уровень сигнала на анализаторе : {} dBuV".format(
                    currentSignalStrength)
                print(time.ctime(), smsText)
                send_sms(smsText)
                time.sleep(10)
                while True:
                    analysisSmallSignalStrenght = snmp_walk()
                    if analysisSmallSignalStrenght[i] < 250:
                        currentSignalStrength = int(analysisSmallSignalStrenght[i]) / 10
                        smsText = "Соколовская 76а: низкий уровень сигнала на анализаторе : {} dBuV".format(
                            currentSignalStrength[i])
                        print(time.ctime(), smsText)
                        send_sms(smsText)
                    break
                    time.sleep(10)
        time.sleep(10)

if __name__ == '__main__':
    daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)
