import netsnmp
import time
from urllib.request import urlopen

def send_sms(text_sms):
    text_sms = text_sms.replace(" ", "+")
    url = f"https://sms.ru/sms/send?api_id=1263F23C-04F1-D64A-EAAD-146773D980FC&to=79059743304,74993221627&msg={text_sms}&json=1"
    res = urlopen(url.decode('utf-8'))

def main():
    oid = netsnmp.Varbind('enterprises.32108.2.4.3.3.1.2')
    while True:
        signalLevel = netsnmp.snmpwalk(oid,
                                       Version=1,
                                       DestHost="172.23.104.1",
                                       Community="public")
        for i in range(len(signalLevel)):
            if int(signalLevel[i]) > 195:
                currentSignalLevel = int(signalLevel[i]) / 10
                # print("Соколовская 76а: высокий уровень сигнала на анализаторе -", int(signalLevel[i]) / 10, "dBuV")
                sms_text = f"Соколовская 76а: высокий уровень сигнала на анализаторе - {currentSignalLevel} dBuV"
                send_sms(sms_text)
        time.sleep(60)

if __name__ == '__main__':
    main()

    '''
    sms_text = {
    "s": "Соколовская 76а: высокий уровень сигнала на анализаторе - 200 dBuV"}
    enc_sms_text = urllib.parse.urlencode(sms_text)
    url = "https://sms.ru/sms/send?api_id=1263F23C-04F1-D64A-EAAD-146773D980FC&to=79059743304&msg="
    f = urllib.request.urlopen(url + enc_sms_text)
    '''