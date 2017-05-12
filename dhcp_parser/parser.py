import re
import redis
import os
import time


ip_mac_regexp = r'(([^:]+):){3} ([^ ]+ ){2}(?P<ip>[^ ]+) [^ ]+ (?P<mac>[^ ]+)'


def process_line(line):
    if 'DHCPOFFER' in line:
        rex = re.search(ip_mac_regexp, line)
        redis_db.set(rex.group("mac"), rex.group("ip"))


def process_file(path):
    file_size = os.path.getsize(path)
    try:
        offset = int(redis_db.get("file:offset", 0))
        while True:
            with open(path) as file_handler:
                offset = 0 if offset > file_size else offset

                while not file_handler.eof():
                    process_line(file_handler.readline())

                redis_db.set("file:offset", file_handler.tell())
            time.sleep(5)

    except (IOError, OSError):
        print("Error opening / processing file")


if __name__ == '__main__':
    redis_db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    try:
        response = redis_db.client_list()
    except (redis.exceptions.ConnectiоnError, ConnectionRefusedError):
        print("Connection refused - Unable to connect to Redis")
    else:
        filepath = "dhcpgen.log"
        process_file(filepath)
