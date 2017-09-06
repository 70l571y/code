import re
import redis
import os
import time
import sys
from other.daemon import daemon_exec

ip_mac_regexp = r'(([^:]+):){3} ([^ ]+ ){2}(?P<ip>[^ ]+) [^ ]+ (?P<mac>[^ ]+)'

path = "/home/sid/PycharmProjects/dhcp/dhcp_parser/dhcpgen.log"

def process_line(line):
    if 'DHCPOFFER' in line:
        rex = re.search(ip_mac_regexp, line)
        redis_db.set(rex.group("mac").replace(':', '-').upper(), rex.group("ip"))


def process_file():
    file_size = os.path.getsize(path)
    try:
        if redis_db.get("file:offset") == None:
            redis_db.set("file:offset", "0")

        offset = int(redis_db.get("file:offset"))
        while True:
            with open(path) as file_handler:
                offset = 0 if offset > file_size else offset

                while True:
                    redis_db.set("file:offset", file_handler.tell())
                    process_line(file_handler.readline())
                    if os.path.getsize(path) == int(redis_db.get("file:offset")):
                        file_handler.close()
                        break
                time.sleep(5)

    except (IOError, OSError):
        print("Error opening / processing file")


if __name__ == '__main__':
    redis_db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    try:
        response = redis_db.client_list()
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print("Connection refused - Unable to connect to Redis")
    else:
        sys.path.append("..")
        pathToPID = '/tmp/roman/daemons/'
        nameOfPID = 'dhcp_parser'
        if not os.path.exists(pathToPID):
            os.makedirs(pathToPID)
        out = {'stdout': pathToPID + nameOfPID + '.log'}
        action = 'start'

        daemon_exec(process_file, action, pathToPID + nameOfPID + '.pid', **out)
