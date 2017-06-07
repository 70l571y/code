import netsnmp
import time
import urllib.request
import urllib.parse

def send_sms(text):
    # text_sms = text_sms.replace(" ", "+")
    sms_text = {"s": text}
    enc_sms_text = urllib.parse.urlencode(sms_text)
    url = f"https://sms.ru/sms/send?api_id=1263F23C-04F1-D64A-EAAD-146773D980FC&to=79059743304&msg="
    f = urllib.request.urlopen(url + enc_sms_text)

def main():
    oid = netsnmp.Varbind('enterprises.32108.2.4.3.3.1.2')
    while True:
        signalStrength = netsnmp.snmpwalk(oid,
                                       Version=1,
                                       DestHost="172.23.104.1",
                                       Community="public")
        for i in range(len(signalStrength)):
            if int(signalStrength[i]) > 200:
                time.sleep(60)
                if int(signalStrength[i] > 200):
                    currentSignalStrength = int(signalStrength[i]) / 10
                    sms_text = f"Соколовская 76а: высокий уровень сигнала на анализаторе : {currentSignalStrength} dBuV"
                    send_sms(sms_text)
                    while True:
                        for k in range(len(signalStrength)):
                            if int(signalStrength[k]) < 200:
                                time.sleep(60)
                                if int(signalStrength[k] < 200):
                                    currentSignalStrength = int(signalStrength[i]) / 10
                                    sms_text = f"Соколовская 76а: низкий уровень сигнала на анализаторе : {currentSignalStrength} dBuV"
                                    send_sms(sms_text)
                                    break
                    time.sleep(60)
        time.sleep(60)

if __name__ == '__main__':
    main()