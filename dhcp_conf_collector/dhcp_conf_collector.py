import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import redis
import re
import os
from other.daemon import daemon_exec
import time
import sys
#import subprocess

sys.path.append("..")
pathToPID = '/tmp/roman/daemons/'
nameOfPID = 'conf_collector'
if not os.path.exists(pathToPID):
    os.makedirs(pathToPID)
out = {'stdout': pathToPID + nameOfPID + '.log'}
action = 'start'


def sql_request(sql):
    try:
        curs.execute(sql)
    except (psycopg2.Error) as error:
        print(error)
        print(time.ctime(), '- В базе данных нет такого устройства, или некорректен следующий запрос:')
        print(sql)
        return 0
    else:
        rows = curs.fetchone()
        return rows


def add_conf_entry(lines):
    f = open('production.conf', 'a')
    f.write(lines)
    f.close()


def check_network_settings(mac_address):
    sql_req_IP = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    result_IP = sql_request(sql_req_IP)
    ip_address = result_IP[5]['ip']
    sql_req_subnet_id = "select subnet_id from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    subnet_id = sql_request(sql_req_subnet_id)
    sql_req_network_address = "select network from subnets where id={};".format(subnet_id[0])
    sql_req_gateway = "select gw from subnets where id={};".format(subnet_id[0])
    network_address = sql_request(sql_req_network_address)
    gateway_address = sql_request(sql_req_gateway)
    return ip_address, network_address, gateway_address


def check_allocation(mac_address):
    # Вернет истину если свитч в красноярском продакшине
    allocation_req = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    allocation = sql_request(allocation_req)
    if allocation == 0:
        return False
    elif allocation == None:
        return False
    elif allocation[4] == 1:
        city_allocation = "select * from allocation where id={};".format(allocation[4])
        result_city = sql_request(city_allocation)
        return True if result_city[2] == 1 else False


def read_config_file(file):
    while True:
        data = file.readline()
        if not data:
            break
        yield data


def check_config_file(mac):
    try:
        with open('production.conf') as file_handler:
            for line in read_config_file(file_handler):
                if mac in line:
                    return True
            return False

            # return False
    except (IOError, OSError):
        print("Error opening / processing file")


def main():
    # # print(check_allocation('00-1E-58-A9-01-36'))
    # print(check_config_file('00:25:11:c3:38:ef'))
    # print(check_network_settings('00-1E-58-A9-01-36'))

    redis_db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    try:
        response = redis_db.client_list()
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print(time.ctime(), "Connection refused - Unable to connect to Redis")
    else:
        mac_regexp = r'((?:[0-9A-F]{2}-){5}[0-9A-F]{2})'
        while True:
            redis_all_keys = redis_db.keys()
            for keys in redis_all_keys:
                redis_current_key = keys.decode('utf-8')
                result = re.findall(mac_regexp, redis_current_key)
                if not result:
                    continue
                if check_allocation(result[0]):
                    print('Fuuuuck yeah!!!!')





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
            curs = conn.cursor()
            main()
    except:
        print(time.ctime(), "Connection server - Failed")

    # else:
    #     main()
        # daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)

        # subprocess.check_call("sudo /etc/init.d/dhcpd restart", shell=True)