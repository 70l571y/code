import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import redis
import re

def sql_request(sql):
    curs.execute(sql)
    rows = curs.fetchone()
    curs.close()
    return rows

def check_network_settings(mac_address):
    sql_req_IP = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    result_IP = sql_request(sql_req_IP)
    return result_IP[5]['ip']
    #сделать булеву проверку на соответствие ip адреса с redis

def check_allocation(mac_address):
    #Вернет истину если свитч в красноярском продакшине
    allocation_req = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    allocation = sql_request(allocation_req)
    return allocation[4]
    # if allocation[4] == 1:
    #     city_allocation = "select * from allocation where id={};".format(allocation[4])
    #     result_city = sql_request(city_allocation)
    #     return True if result_city[2] == 1 else False


    # sql = "select * from allocation where id={};".format(result_sql_request_allocation[4])
    # result = sql_request(sql)
    # return result

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
                # print(check_allocation(result[0]))
                print(check_allocation('30-71-B2-61-C3-EF'))
            break



if __name__ == "__main__":
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
            conn = psycopg2.connect(database="switchbase", user=server.ssh_username, password=server.ssh_password,
                                    host="localhost",
                                    port=server.local_bind_port)
            curs = conn.cursor()
            read_redis()

    except:
        print("SSH server connection - Failed")



'''
import psycopg2
import subprocess

connection = psycopg2.connect(
    database=database,
    user=username,
    password=password,
    host=host,
    port=port
)

print connection.closed # 0

# restart the db externally
subprocess.check_call("sudo /etc/init.d/postgresql restart", shell=True)

# this query will fail because the db is no longer connected
try:
    cur = connection.cursor()
    cur.execute('SELECT 1')
except psycopg2.OperationalError:
    pass

print connection.closed # 2
'''