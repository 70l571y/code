import time
import random


def rand_mac():
    return "%02x:%02x:%02x:%02x:%02x:%02x" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


def rand_ip():
    return "%d:%d:%d:%d" % (random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255))

# print(rand_mac())
# print(rand_ip())
while True:
    mac = str(rand_mac())
    ip = str(rand_ip())
    f = open(f"dhcpgen.log", 'a')
    f.write(f"Apr  4 04:30:01 src@localhost dhcpd: DHCPOFFER on {ip} to {mac} via 109.226.250.32" + "\n")
    time.sleep(1)
