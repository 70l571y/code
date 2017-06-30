"""
    1) Берет i-й мак адрес с БД Редис
    2) Ищет свитч по мак адресу (взятый с редиса) в продакшине
    3) Если свитч в продакшине, то смотрит есть ли в DHCP конфиге запись с данным мак адресом
        3.1) Если свитч не в продакшине, то ищет данный свитч в DHCP конфиге по мак адресу
        3.2) Если свитч есть в DHCP конфиге (которого нет в базе), то удалаяет данную запись,
            перезагрузает DHCP сервер и переходит в п.1)
        3.3) Если свитча нет в DHCP конфиге, то переходит в п.1)
    4) Если запись в DHCP конфиге есть, то сравнивает его сетевые настройки
        4.1) Если записи с данный мак адресом в DHCP конфиге нет, то добавляет данную запись
            и перезагрузает DHCP сервер
    5) Если настройки верные, то переходит в п.1)
        5.1) Если настройки неверные, то удаляет данную запись и добавляет новую запись с
            верными сетевыми настройками и перезагрузает DHCP сервер

    Используемые функции:
    config_entry - сформированная запись в конфиг DHCP сервера
    reboot_dhcp_server - перезагрузка DHCP сервера
    sql_request - запрос в БД по заданному sql запросу извне и возвращение ответа от базы
    add_conf_entry - добавление записи в конфиг DHCP сервера по заданному мак адресу из БД
    del_conf_entry - удаление записи из конфига DHCP сервера по заданному мак адресу
    get_network_settings - получение сетевых настроек хоста из базы по заданному мак адресу
    check_allocation - проверка есть ли свитч в продакшине
    search_mac_address_on_config_file - поиск заданного мак адреса в конфиге DHCP сервера
    main - бесконечное считывания мак адресов с БД Редис
    """

import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import redis
import re
import os
from other.daemon import daemon_exec
import time
import sys
import subprocess
import ipaddress


production_config_file = '/etc/dhcpd/production.conf'

#configs and firmwares settings
tftp_server_name = '80.65.17.254'
dlink_dgs_1210_28_me_b1_config_bootfile_name = 'cfg1210.cfg'
option_150 = tftp_server_name


#daemon settings
sys.path.append("..")
pathToPID = '/tmp/roman/daemons/'
nameOfPID = 'conf_collector'
if not os.path.exists(pathToPID):
    os.makedirs(pathToPID)
out = {'stdout': pathToPID + nameOfPID + '.log'}
action = 'start'

def config_entry(mac_address):
    network_settings = get_network_settings(mac_address)
    host_network = network_settings[0]
    host_ip_address = network_settings[1]
    host_gateway = network_settings[2]
    host_mac_address = network_settings[3]
    host_models_name = network_settings[4]
    ip = ipaddress.IPv4Network(host_network)

    write_entry = "subnet " + host_network[:-3] + " netmask " + str(ip.netmask) + " {\n" \
                  "authoritative;\noption routers " + host_gateway + ";\n" \
                  "option tftp-server-name \"" + tftp_server_name + "\";\noption bootfile-name \"" + \
                  dlink_dgs_1210_28_me_b1_config_bootfile_name + "\";\n" \
                  "option option-150 " + option_150 + ";\nhost " + host_models_name + " {\n" \
                  "hardware ethernet " + host_mac_address + ";\nfixed-address " + host_ip_address + ";\n}\n}\n}"
    return write_entry

def reboot_dhcp_server():
    subprocess.call(["/etc/init.d/dhcpd", "restart"])


def sql_request(sql):
    try:
        curs.execute(sql)
    except (psycopg2.Error) as error:
        print(error)
        print(time.ctime(), '- В базе данных нет такого устройства, или некорректен следующий запрос:\n', sql)
        return 0
    else:
        rows = curs.fetchone()
        return rows


def add_conf_entry(mac_address):
    # network_settings = get_network_settings(mac_address)
    # host_network = network_settings[0]
    # host_ip_address = network_settings[1]
    # host_gateway = network_settings[2]
    # host_mac_address = network_settings[3]
    # host_models_name = network_settings[4]
    # ip = ipaddress.IPv4Network(host_network)
    #
    # write_entry = "subnet " + host_network[:-3] + " netmask " + str(ip.netmask) + " {\n" \
    #               "authoritative;\noption routers " + host_gateway + ";\n" \
    #               "option tftp-server-name \"" + tftp_server_name + "\";\noption bootfile-name \"" + \
    #               dlink_dgs_1210_28_me_b1_config_bootfile_name + "\";\n" \
    #               "option option-150 " + option_150 + ";\nhost " + host_models_name + " {\n" \
    #               "hardware ethernet " + host_mac_address + ";\nfixed-address " + host_ip_address + ";\n}\n}\n}"
    host_entry = config_entry(mac_address)

    with open(production_config_file, 'r') as dhcpd_conf_file:
        config_file = dhcpd_conf_file.readlines()

    with open(production_config_file, 'w') as save_dhcpd_conf_file:
        config_file.append(host_entry)
        save_dhcpd_conf_file.writelines(config_file)
        reboot_dhcp_server()


def del_conf_entry(mac_address):
    try:
        with open(production_config_file, 'r') as dhcpd_conf_file:
            config_file = dhcpd_conf_file.readlines()
            search_entry = "hardware ethernet {} ;".format(mac_address)
            for i in range(len(config_file)):
                if config_file[i].rstrip() == search_entry:
                    break

        with open(production_config_file, 'w') as save_dhcpd_conf_file:
            del config_file[i - 6:i + 4]
            save_dhcpd_conf_file.writelines(config_file)
            reboot_dhcp_server()
    except (IOError, OSError):
        print("Error opening / processing file")


def get_network_settings(mac_address):
    sql_req_IP = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    result_IP = sql_request(sql_req_IP)
    # sql_req_models_name = ""
    # result_models_name = sql_request((sql_req_models_name))
    # models_name = result_models_name
    ip_address = result_IP[5]['ip']
    sql_req_subnet_id = "select subnet_id from switches where switch_data @>'{\"mac\": \"" + mac_address + "\"}';"
    subnet_id = sql_request(sql_req_subnet_id)
    sql_req_network_address = "select network from subnets where id={};".format(subnet_id[0])
    sql_req_gateway = "select gw from subnets where id={};".format(subnet_id[0])
    network_address = sql_request(sql_req_network_address)
    gateway_address = sql_request(sql_req_gateway)
    return network_address, ip_address, gateway_address, mac_address, models_name


def checking_for_network_settings_matches(mac_address):
    with open('dhcp_conf_prod.conf', 'r') as dhcpd_conf_file:
        search_mac_address = "hardware ethernet " + mac_address + ";\n"
        config_file = dhcpd_conf_file.readlines()
        host_entry = config_entry(mac_address)
        if search_mac_address_on_config_file in config_file:
            found_entry = ''.join(f[f.index(search_mac_address) - 7: f.index(search_mac_address) + 2])
            if host_entry[:-5] == found_entry:
                return True
            else:
                return False


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


def search_mac_address_on_config_file(mac):
    try:
        search_mac_address = "hardware ethernet " + mac + ";\n"
        with open(production_config_file) as file_handler:
            config_file = file_handler.readlines()
            if search_mac_address in config_file:
                return True
            else:
                return False
    except (IOError, OSError):
        print("Error opening / processing file")


def main():
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
                if check_allocation(result[0]) and search_mac_address_on_config_file(result[0]):

                elif search_mac_address_on_config_file(result[0]):
                    del_conf_entry(result[0])
                    continue
                else:
                    continue


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