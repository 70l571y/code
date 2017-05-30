import telnetlib
from time import sleep

print("Starting Client...")
host = "192.168.225.72"
user = "sidorkin_r"
password = "ghfdjcelbt"
timeout = 10

print("Connecting...")
session = telnetlib.Telnet(host, 23, timeout)


print("Autorisation...")
session.read_until(b"Username: ")
session.write(user.encode('ascii') + b"\n")
session.write(password.encode('ascii') + b"\n")
print("Reading...")

session.write(b"show firmware information" + b"\n")
while True:
    line = session.read_until(b"\n")
    # print(line)
    if b'Current    : image one' in line:
        print("firmware in 1 slot")
        break
    elif b'Current    : image two' in line:
        print("firmware in 2 slot")
        session.write(
            b"download firmware_fromTFTP 80.65.17.254 AutoconfigFirm/DGS-1210-28/dgs-1210-28me-a1-6-13-b028-all.hex image_id 1" + b"\n")

        while True:
            newline = session.read_until(b"\n")
            sleep(0.1)
            print(newline)
            if b'Download firmware...................... Done' in newline:
                print("firmware download - complete")
                print("Please wait, programming flash...")
            if b'programming flash......... Done' in newline:
                print("programming flash - complete")
        break
        session.write(b"config firmware image_id 1 boot_up" + b"\n")

        session.write(b"save" + b"\n")

session.write(b"logout" + b"\n")
session.close()
