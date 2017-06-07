import netsnmp

oid = netsnmp.Varbind('enterprises.32108.2.4.3.3.1.2')

result = netsnmp.snmpwalk(oid,
                          Version=1,
                          DestHost="172.23.104.1",
                          Community="public")

if int(result[1]) > 167:
    print("alarmmmm")
print(result[1])