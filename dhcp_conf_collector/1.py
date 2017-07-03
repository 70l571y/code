import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import redis
import re
import os
from other.daemon import daemon_exec
import time
import sys
# import subprocess
import ipaddress

sys.path.append("..")
# production_config_file = '/home/sid/Documents/production.conf'
production_config_file = '/home/sid/PycharmProjects/dhcp/dhcp_conf_collector/production.conf'


# configs and firmwares settings
tftp_server_name = '80.65.17.254'
option_150 = tftp_server_name


def get_config_file_name(model_name):
    # для каждой модели следует написать свой конфиг
    bootfile_name = ""
    if model_name == 'DGS-1210-28/ME':
        bootfile_name = "cfg1210.cfg"
    elif model_name == 'DES-3526':
        bootfile_name = 'cfg3526.cfg'
    else:
        print('Отсутствует файл конфигурации для модели:', model_name)
    return bootfile_name


def config_entry(mac_address):
    print('config_entry')
    network_settings = get_network_settings(
        mac_address.lower().replace('-', ':'))
    print('config_entry/network_settings', network_settings)
    host_ip_address = network_settings[1]
    print('config_entry/host_ip_address', host_ip_address)
    host_gateway = network_settings[2]
    print('config_entry/host_gateway', host_gateway)
    host_mac_address = network_settings[3].lower()
    print('config_entry/host_mac_address', host_mac_address)
    host_models_name = network_settings[4]
    print('config_entry/host_models_name', host_models_name)
    host_network = str(ipaddress.IPv4Network(
        network_settings[0]).network_address)
    print('config_entry/host_network', host_network)
    ip_netmask = str(ipaddress.IPv4Network(network_settings[0]).netmask)
    print('config_entry/ip_netmask', ip_netmask)
    config_bootfile_name = get_config_file_name(host_models_name)
    print('config_entry/config_bootfile_name', config_bootfile_name)

    write_entry = "subnet " + host_network + " netmask " + ip_netmask + " {\n" \
                  "authoritative;\noption routers " + host_gateway + ";\n" \
                  "option tftp-server-name \"" + tftp_server_name + "\";\noption bootfile-name \"" + \
                  config_bootfile_name + "\";\n" \
                  "option option-150 " + option_150 + ";\nhost " + host_models_name + " {\n" \
                  "hardware ethernet " + host_mac_address + \
        ";\nfixed-address " + host_ip_address + ";\n}\n}\n}"
    print('config_entry/write_entry', write_entry)
    return write_entry


def reboot_dhcp_server():
    # subprocess.call(["/etc/init.d/dhcpd", "restart"])
    print('DHCP - перезагружен')


def sql_request(sql):
    server = SSHTunnelForwarder(
        (config['ssh_host'], int(config['ssh_port'])),
        ssh_password=config['password'],
        ssh_username=config['username'],
        remote_bind_address=('127.0.0.1', 5432))
    server.start()
    # with open('/home/sid/PycharmProjects/dhcp/other/config.json') as f:
    conn = psycopg2.connect(database="switchbase", user=server.ssh_username, password=server.ssh_password,
                            host="localhost",
                            port=server.local_bind_port)
    print('sql_request/законнектился к базе')
    curs = conn.cursor()
    print('sql_request/установка курсора')
    print('sql_request/начало запроса')
    curs.execute(sql)
    print('sql_request/конец запроса')
    result = curs.fetchone()
    return result

    # try:
    #     print('курсор еще не выполнился')
    #     curs.execute(sql)
    #     print('курсор выполнился')
    # except (psycopg2.Error) as error:
    #     print(error)
    #     print(time.ctime(
    #     ), '- В базе данных нет такого устройства, или некорректен следующий запрос:\n', sql)
    #     return 0
    # else:
    #     return curs.fetchone()


def add_conf_entry(mac_address):
    print('add_conf_entry')
    host_entry = config_entry(mac_address.lower().replace('-', ':'))
    print('add_conf_entry/host_entry', host_entry)

    try:

        with open(production_config_file, 'r') as dhcpd_conf_file:
            print('add_conf_entry/open file readlines')
            config_file = dhcpd_conf_file.readlines()
            print('add_conf_entry/config_file', config_file)
    except (IOError, OSError):
        print("add_conf_entry/не могу открыть файл для чтения")
    try:
        with open(production_config_file, 'w') as save_dhcpd_conf_file:
            # удалить лишнюю фигурную скобку в конце
            del config_file[len(config_file) - 1]
            config_file.append(host_entry)
            save_dhcpd_conf_file.writelines(config_file)
            print('add_conf_entry/open file write')
    except (IOError, OSError):
        print("add_conf_entry/не могу открыть файл для записи")


def del_conf_entry(mac_address):
    print('del_conf_entry')
    try:
        with open(production_config_file) as dhcpd_conf_file:
            config_file = dhcpd_conf_file.readlines()
            search_entry = "hardware ethernet {};".format(
                mac_address.lower().replace('-', ':'))
            for i in range(len(config_file)):
                if config_file[i].rstrip() == search_entry:
                    break
        with open(production_config_file, 'w') as save_dhcpd_conf_file:
            del config_file[i - 8:i + 3]
            save_dhcpd_conf_file.writelines(config_file)
    except (IOError, OSError):
        print("del_conf_entry/Error opening / processing file")


def get_network_settings(mac_address):
    print('get_network_settings')
    sql_req_ip = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address.upper(
    ).replace(':', '-') + "\"}';"
    ip_address = sql_request(sql_req_ip)[5]['ip']
    print('get_network_settings/ip address', ip_address)
    sql_req_models_id = "select model_id from switches where switch_data @>'{\"mac\": \"" + mac_address.upper(
    ).replace(':', '-') + "\"}';"
    models_id = sql_request(sql_req_models_id)[0]
    print('get_network_settings/models_id', models_id)
    sql_req_models_name = "select data from models where id=" + \
        str(models_id) + ";"
    models_name = sql_request(sql_req_models_name)[0]['name']
    print('get_network_settings/models_name', models_name)
    sql_req_subnet_id = "select subnet_id from switches where switch_data @>'{\"mac\": \"" + mac_address.upper(
    ).replace(':', '-') + "\"}';"
    subnet_id = sql_request(sql_req_subnet_id)
    print('get_network_settings/subnet_id', subnet_id)
    sql_req_network_address = "select network from subnets where id={};".format(subnet_id[
                                                                                0])
    sql_req_gateway = "select gw from subnets where id={};".format(subnet_id[
                                                                   0])
    network_address = sql_request(sql_req_network_address)[0]
    print('get_network_settings/network_address', network_address)
    gateway_address = sql_request(sql_req_gateway)[0]
    print('get_network_settings/gateway_address', gateway_address)
    return network_address, ip_address, gateway_address, mac_address.lower().replace('-', ':'), models_name


def checking_for_network_settings_matches(mac_address):
    with open(production_config_file) as dhcpd_conf_file:
        search_mac_address = "hardware ethernet " + \
            mac_address.lower().replace('-', ':') + ";\n"
        config_file = dhcpd_conf_file.readlines()
        host_entry = config_entry(mac_address.lower().replace('-', ':'))
        if search_mac_address in config_file:
            found_entry = ''.join(config_file[config_file.index(
                search_mac_address) - 7: config_file.index(search_mac_address) + 2])
            return True if host_entry[:-5] == found_entry else False


def check_allocation(mac_address):
    print('check allocation')
    # Вернет истину если свитч в красноярском продакшине
    allocation_req = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address.upper(
    ).replace(':', '-') + "\"}';"
    allocation = sql_request(allocation_req)
    if (allocation == 0) or (allocation == None):
        return False
    elif allocation[4] == 1:
        print('check_allocation/allocation is producion')
        city_allocation = "select * from allocation where id={};".format(allocation[
                                                                         4])
        print('check_allocation/запрос allocation', city_allocation)
        result_city = sql_request(city_allocation)
        return True if result_city[2] == 1 else False


def search_mac_address_on_config_file(mac_address):
    print('search_mac_address_on_config_file')
    try:
        search_mac_address = "hardware ethernet " + \
            mac_address.lower().replace('-', ':') + ";\n"
        with open(production_config_file) as file_handler:
            config_file = file_handler.readlines()
            return True if search_mac_address in config_file else False
    except (IOError, OSError):
        print("search_mac_address_on_config_file/Error opening / processing file")


def main():
    # переключалка для ребута DHCP сервера
    dhcp_server_reboot_switch = 0
    redis_db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    try:
        response = redis_db.client_list()
        print('main/redis response')
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print(time.ctime(), "Connection refused - Unable to connect to Redis")
    else:
        mac_regexp = r'((?:[0-9A-F]{2}-){5}[0-9A-F]{2})'
        while True:
            if dhcp_server_reboot_switch:
                print('main/dhcp_server_reboot_switch')
                time.sleep(5)
                reboot_dhcp_server()
                dhcp_server_reboot_switch = 0
                time.sleep(5)
            redis_all_keys = redis_db.keys()
            print('main/get redis_all_keys')
            for keys in redis_all_keys:
                print('main/redis get keys')
                redis_current_key = keys.decode('utf-8')
                print('main/get redis_current_key:', redis_current_key)
                current_mac_address = re.findall(
                    mac_regexp, redis_current_key)
                print('main/get current_mac_address', current_mac_address)
                if not current_mac_address:
                    continue
                print('main/check_allocation -', check_allocation(
                    current_mac_address[0]))
                if check_allocation(current_mac_address[0]):
                    print('main/search_mac_address_on_config_file -',
                          search_mac_address_on_config_file(current_mac_address[0]))
                    if search_mac_address_on_config_file(current_mac_address[0]):
                        print('main/checking_for_network_settings_matches -',
                              checking_for_network_settings_matches)
                        if checking_for_network_settings_matches(current_mac_address[0]):
                            continue
                        else:
                            del_conf_entry(current_mac_address[0])
                            dhcp_server_reboot_switch = 1
                            continue
                    else:
                        print('main/add_conf_entry')
                        add_conf_entry(current_mac_address[0])
                        dhcp_server_reboot_switch = 1
                        print('main/dhcp_server_reboot_switch')
                        continue
                elif search_mac_address_on_config_file(current_mac_address[0]):
                    del_conf_entry(current_mac_address)
                    continue
                else:
                    continue
            # time.sleep(0.1)


if __name__ == "__main__":
    f = open('/home/sid/PycharmProjects/dhcp/other/config.json')
    config = json.load(f)

    sys.path.append("..")
    pathToPID = '/tmp/roman/daemons/'
    nameOfPID = 'testerovich'
    if not os.path.exists(pathToPID):
        os.makedirs(pathToPID)
    out = {'stdout': pathToPID + nameOfPID + '.log'}
    action = 'start'
    daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)