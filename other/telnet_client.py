import telnetlib
import getpass
from time import sleep


def upgrade_firmware():
    print("Starting Client...")
    host = "192.168.225.72"
    timeout = 10

    print("Connecting...")
    session_upd_firm = telnetlib.Telnet(host, 23, timeout)

    print("Autorisation...")
    user = input("Enter username: ")
    password = getpass.getpass()
    session_upd_firm.read_until(b"Username: ")
    session_upd_firm.write(user.encode('ascii') + b"\n")
    session_upd_firm.write(password.encode('ascii') + b"\n")
    print("Reading...")

    session_upd_firm.write(b"show firmware information" + b"\n")

    while True:
        line = session_upd_firm.read_until(b"\n")
        # print(line)
        if b'Current    : image one' in line:
            current_firmware = 1
            break

        elif b'Current    : image two' in line:
            current_firmware = 2
            break

    firmware = f"download firmware_fromTFTP 80.65.17.254 AutoconfigFirm/DGS-1210-28/dgs-1210-28me-a1-6-13-b028-all.hex image_id {current_firmware}"
    boot_up = f"config firmware image_id {current_firmware} boot_up"

    session_upd_firm.write(firmware.encode('ascii') + b"\n")
    while True:
        newline = session_upd_firm.read_until(b"\n")
        sleep(0.1)
        print(newline)
        if b'Download firmware...................... Done' in newline:
            print("firmware download - complete")
            print("Please wait, programming flash...")
        if b'programming flash......... Done' in newline:
            print("programming flash - complete")
        break

    session_upd_firm.write(boot_up.encode('ascii') + b"\n")
    session_upd_firm.write(b"save" + b"\n")
    session_upd_firm.write(b"reboot force_agree" + b"\n")
    session_upd_firm.close()

def upgrade_config():
    print("Starting Client...")
    host = "192.168.225.72"
    timeout = 10
    print("Connecting...")
    session_upd_config = telnetlib.Telnet(host, 23, timeout)

    config = b"download cfg_fromFTP ftp://ftp:rhtyltkmivtyltkm@10.90.90.1/AutoconfigCfg/DGS-1210-28/dgs1210-28.cfg config_id 1\n"
    session_upd_config.write(config.encode('ascii'))
    session_upd_config.close()

def testing():
    print("Starting Client...")
    host = "192.168.225.72"
    timeout = 3
    variables = f"conf ports {timeout} state disable\n"
    print("Connecting...")
    testing_session = telnetlib.Telnet()
    testing_session.open(host, 23, timeout)

    print("Autorisation...")
    user = input("Enter username: ")
    password = getpass.getpass()
    testing_session.read_until(b"Username: ")
    testing_session.write(user.encode('ascii') + b"\n")
    testing_session.write(password.encode('ascii') + b"\n")
    print("Reading...")

    testing_session.write(variables.encode('ascii') + b"\n")
    # print(testing_session.read_until(b"Auto"))
    testing_session.write(b"logout\n")
    testing_session.close()

if __name__ == '__main__':
    testing()
