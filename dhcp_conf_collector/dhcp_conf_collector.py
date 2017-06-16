import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import redis
import re

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
            print("SSH server connected")
            try:
                conn = psycopg2.connect(database="switchbase", user=server.ssh_username, password=server.ssh_password, host="localhost",
                                        port=server.local_bind_port)
                curs = conn.cursor()
                print("DB connected across SSH Thunnel")
                curs.execute(sql_request)
                rows = curs.fetchone()
                curs.close()
                return rows
            except:
                print("DB connection - Failed")
    except:
        print("SSH server connection - Failed")


def check_IP(mac_address):
    sql = "select switch_data from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    result = sql_request(sql)
    return result[0]['ip']


def read_redis():
    redis_db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    try:
        response = redis_db.client_list()
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print("Connection refused - Unable to connect to Redis")
    else:
        mac_regexp = r'((?:[0-9a-f]{2}:){5}[0-9a-f]{2})'
        while True:
            redis_all_keys = redis_db.keys()
            for i in redis_all_keys:
                redis_current_key = i.decode('utf-8')
                result = re.findall(mac_regexp, redis_current_key)
                if not result: #так как будут пустые записи в БД, которые не соответствуют mac_regexp
                    continue
                print(result[0])
                # check_IP(result[0])
            print(check_IP(redis_current_key))
            break



def main():
    read_redis()

        # print(sql_request(sql))
        # rkeys = redis_db.keys()
        # print(rkeys)

if __name__ == "__main__":
	main()