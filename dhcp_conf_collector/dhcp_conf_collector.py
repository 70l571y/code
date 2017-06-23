import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import redis
import re
import os
from daemon import daemon_exec
import time
#import subprocess

pathToPID = '/tmp/roman/daemons/'
nameOfPID = 'conf_collector'
if not os.path.exists(pathToPID):
    os.makedirs(pathToPID)
out = {'stdout': pathToPID + nameOfPID + '.log'}
action = 'stop'

def sql_request(sql):
    curs.execute(sql)
    rows = curs.fetchone()
    return rows

def check_network_settings(mac_address):
    sql_req_IP = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    result_IP = sql_request(sql_req_IP)
    return result_IP[5]['ip']
    #сделать булеву проверку на соответствие ip адреса с redish

def check_allocation(mac_address):
    #Вернет истину если свитч в красноярском продакшине
    allocation_req = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    allocation = sql_request(allocation_req)
    if allocation[4] == 1:
        city_allocation = "select * from allocation where id={};".format(allocation[4])
        result_city = sql_request(city_allocation)
        return True if result_city[2] == 1 else False

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
                if not result:
                    continue
                print('mac адрес: ' + result[0] + ' - успешно проверен')
                time.sleep(1)
                # print(check_allocation('70:62:f8:53:1f:e7'))
                # if check_allocation(result[0])
                # break
            # break



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
            conn = psycopg2.connect(database="switchbase", user=server.ssh_username, password=server.ssh_password,
                                    host="localhost",
                                    port=server.local_bind_port)

    except:
        print("Connection server - Failed")

    else:
        curs = conn.cursor()
        daemon_exec(read_redis, action, pathToPID + nameOfPID + '.pid', **out)
        # read_redis()




#subprocess.check_call("sudo /etc/init.d/dhcpd restart", shell=True)
