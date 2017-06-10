import netsnmp
import time
import urllib.request
import urllib.parse
from daemon import daemon_exec

fn = '/tmp/roman/signal_strenght'
out = {'stdout': fn + '.log'}
action = 'stop'

def send_sms(text):
    sms_text = {text}
    enc_sms_text = urllib.parse.urlencode(sms_text)
    url = "https://sms.ru/sms/send?api_id=1263F23C-04F1-D64A-EAAD-146773D980FC&to=79059743304&msg="
    #url = "https://sms.ru/sms/send?api_id=CCE170B7-6F1F-1614-EB4F-C987F279B26C&to=79135710835&msg="
    f = urllib.request.urlopen(url + enc_sms_text)

def main():
    oid = netsnmp.Varbind('enterprises.32108.2.4.3.3.1.2')
    while True:
        signalStrength = netsnmp.snmpwalk(oid, Version=1, DestHost="172.23.104.1", Community="public")
        for i in range(len(signalStrength)):
            if int(signalStrength[i]) > 210:
                time.sleep(60)
                currentSignalStrength = int(signalStrength[i]) / 10
                sms_text = f"Соколовская 76а: высокий уровень сигнала на анализаторе : {currentSignalStrength} dBuV"
                send_sms(sms_text)
                time.sleep(60)
                while True:
                    for k in range(len(signalStrength)):
                        if int(signalStrength[k]) < 200:
                            currentSignalStrength = int(signalStrength[i]) / 10
                            sms_text = f"Соколовская 76а: низкий уровень сигнала на анализаторе : {currentSignalStrength} dBuV"
                            send_sms(sms_text)
                            break
                        time.sleep(60)


        time.sleep(60)

if __name__ == '__main__':
    daemon_exec(main, action, fn + '.pid', **out)