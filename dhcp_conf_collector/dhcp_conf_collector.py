import psycopg2
from sshtunnel import SSHTunnelForwarder
import json

def main():
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

            # sql = "select * from tabelka"
            # curs.execute(sql)
            # rows = curs.fetchall()
            # print(rows)
    except:
        print("Connection Failed")

if __name__ == "__main__":
	main()