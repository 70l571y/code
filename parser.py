import re
import redis
import os
import time


def read_log_file(line):
    ip_mac_regexp = r'(([^:]+):){3} ([^ ]+ ){2}(?P<ip>[^ ]+) [^ ]+ (?P<mac>[^ ]+)'
    if 'DHCPOFFER' in line:
        rex = re.search(ip_mac_regexp, line)
        redis_db.set(rex.group("mac"), rex.group("ip"))


def process_file(path):

    file_size = os.path.getsize(path)
    try:
        while True:
            if redis_db.get("file:offset") == None:
                redis_db.set("file:offset", "0")
            file_handler = open(path)
            if int(redis_db.get("file:offset")) > file_size:
                file_handler.seek(0)
            else:
                file_handler.seek(int(redis_db.get("file:offset")))

            while True:
                line = file_handler.readline()
                redis_db.set("file:offset", file_handler.tell())
                read_log_file(line)
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
        filepath = "dhcpgen.log"
        process_file(filepath)
