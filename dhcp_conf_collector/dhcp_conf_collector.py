import psycopg2
from sshtunnel import SSHTunnelForwarder
import json

def sql_request(sql_request):
    with open('/home/sid/PycharmProjects/dhcp/other/config.json') as f:
        config = json.load(f)
    try:
        with SSHTunnelForwarder(
                (config['ssh_host'], int(config['ssh_port'])),
                ssh_password=config['password'],
                ssh_username=config['username'],
                remote_bind_address=('127.0.0.1', 5432)) as server:
            server.start()
            print("server connected")
            conn = psycopg2.connect(database="switchbase", user=server.ssh_username, password=server.ssh_password, host="localhost",
                                    port=server.local_bind_port)
            curs = conn.cursor()
            print("database connected")
            curs.execute(sql_request)
            rows = curs.fetchall()
            return rows
    except:
        print("Connection Failed")

def main():
    sql = "select * from switches where switch_data @>'{\"mac\": \"30-71-B2-61-C3-EF\"}';"
    # Перечисления столбцов: id   | model_id | tkd_id | subnet_id | allocation_id | switch_data | users | creation_date | transport_data | topo | migrated
    # [(16544, 333, 5618, 328, 1, {'ip': '192.168.19.50', 'mac': '30-71-B2-61-C3-EF', 'serial': '1602260047N0240', 'location': '', 'original_mac': '30-71-B2-61-C3-EF'}, {'creator_id': '553'}, datetime.datetime(2016, 8, 19, 16, 18, 4, 274144), {}, '16544', False)]
    print(sql_request(sql))

if __name__ == "__main__":
	main()