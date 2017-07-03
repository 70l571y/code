"""
    1) Берет i-й мак адрес с БД Редис
    2) Ищет свитч по мак адресу (взятый с редиса) в продакшине
    3) Если свитч в продакшине, то смотрит есть ли в DHCP конфиге запись с данным мак адресом
        3.1) Если свитч не в продакшине, то ищет данный свитч в DHCP конфиге по мак адресу
        3.2) Если свитч есть в DHCP конфиге (которого нет в базе), то удалаяет данную запись,
             и переходит в п.1)
        3.3) Если свитча нет в DHCP конфиге, то переходит в п.1)
    4) Если запись в DHCP конфиге есть, то сравнивает его сетевые настройки (switchbase с настройками конфига)
        4.1) Если записи с данный мак адресом в DHCP конфиге нет, то добавляет данную запись
    5) Если настройки верные, то переходит в п.1)
        5.1) Если настройки неверные, то удаляет данную запись и добавляет новую запись с
            верными сетевыми настройками
    6) Когда обходит все записи Редиса перезагрузает DHCP сервер (если были изменения в конфиге)
    Используемые функции:
    get_config_file_name - получение названия файла конфигурации модели для ф-ии config_entry
    config_entry - сформированная запись в конфиг DHCP сервера
    reboot_dhcp_server - перезагрузка DHCP сервера
    sql_request - запрос в БД по заданному sql запросу извне и возвращение ответа от базы
    add_conf_entry - добавление записи в конфиг DHCP сервера по заданному мак адресу из БД
    del_conf_entry - удаление записи из конфига DHCP сервера по заданному мак адресу
    get_network_settings - получение сетевых настроек хоста из базы по заданному мак адресу
    checking_for_network_settings_matches - проверяет, есть ли актуальная запись в конфиге
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


# production_config_file = '/etc/dhcpd/production.conf'
production_config_file = 'production.conf'

# configs and firmwares settings
tftp_server_name = '80.65.17.254'
option_150 = tftp_server_name


# daemon settings
sys.path.append("..")
pathToPID = '/tmp/roman/daemons/'
nameOfPID = 'conf_collector'
if not os.path.exists(pathToPID):
    os.makedirs(pathToPID)
out = {'stdout': pathToPID + nameOfPID + '.log'}
action = 'start'


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
    network_settings = get_network_settings(mac_address.lower())
    host_ip_address = network_settings[1]
    host_gateway = network_settings[2]
    host_mac_address = network_settings[3].lower()
    host_models_name = network_settings[4]
    host_network = str(ipaddress.IPv4Network(
        network_settings[0]).network_address)
    ip_netmask = str(ipaddress.IPv4Network(network_settings[0]).netmask)
    config_bootfile_name = get_config_file_name(host_models_name)

    write_entry = "subnet " + host_network + " netmask " + ip_netmask + " {\n" \
                  "authoritative;\noption routers " + host_gateway + ";\n" \
                  "option tftp-server-name \"" + tftp_server_name + "\";\noption bootfile-name \"" + \
                  config_bootfile_name + "\";\n" \
                  "option option-150 " + option_150 + ";\nhost " + host_models_name + " {\n" \
                  "hardware ethernet " + host_mac_address + \
                  ";\nfixed-address " + host_ip_address + ";\n}\n}\n}"
    return write_entry


def reboot_dhcp_server():
    # subprocess.call(["/etc/init.d/dhcpd", "restart"])
    print('reboot dhcp server...')


def sql_request(sql):
    try:
        curs.execute(sql)
    except (psycopg2.Error) as error:
        print(error)
        print(time.ctime(), '- В базе данных нет такого устройства, или некорректен следующий запрос:\n', sql)
        return 0
    else:
        return curs.fetchone()


def add_conf_entry(mac_address):
    host_entry = config_entry(mac_address.lower().replace('-', ':'))

    with open(production_config_file) as dhcpd_conf_file:
        config_file = dhcpd_conf_file.readlines()

    with open(production_config_file, 'w') as save_dhcpd_conf_file:
        del config_file[len(config_file) - 1]  # удалить лишнюю фигурную скобку в конце
        config_file.append(host_entry)
        save_dhcpd_conf_file.writelines(config_file)


def del_conf_entry(mac_address):
    try:
        with open(production_config_file) as dhcpd_conf_file:
            config_file = dhcpd_conf_file.readlines()
            search_entry = "hardware ethernet {};".format(mac_address.lower().replace('-', ':'))
            for i in range(len(config_file)):
                if config_file[i].rstrip() == search_entry:
                    break
        with open(production_config_file, 'w') as save_dhcpd_conf_file:
            del config_file[i - 8:i + 3]
            save_dhcpd_conf_file.writelines(config_file)
    except (IOError, OSError):
        print("Error opening / processing file")


def get_network_settings(mac_address):
    sql_req_ip = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address.upper().replace(':', '-') + "\"}';"
    sql_req_models_id = "select model_id from switches where switch_data @>'{\"mac\": \"" + mac_address.upper().replace(':', '-') + "\"}';"
    models_id = sql_request(sql_req_models_id)[0]
    sql_req_models_name = "select data from models where id=" + str(models_id) + ";"
    sql_req_subnet_id = "select subnet_id from switches where switch_data @>'{\"mac\": \"" + mac_address.upper().replace(':', '-') + "\"}';"
    subnet_id = sql_request(sql_req_subnet_id)
    sql_req_network_address = "select network from subnets where id={};".format(subnet_id[0])
    sql_req_gateway = "select gw from subnets where id={};".format(subnet_id[0])
    network_address = sql_request(sql_req_network_address)[0]
    ip_address = sql_request(sql_req_ip)[5]['ip']
    gateway_address = sql_request(sql_req_gateway)[0]
    models_name = sql_request(sql_req_models_name)[0]['name']
    return network_address, ip_address, gateway_address, mac_address.lower().replace('-', ':'), models_name


def checking_for_network_settings_matches(mac_address):
    with open(production_config_file) as dhcpd_conf_file:
        search_mac_address = "hardware ethernet " + mac_address.lower().replace('-', ':') + ";\n"
        config_file = dhcpd_conf_file.readlines()
        host_entry = config_entry(mac_address.lower().replace('-', ':'))
        if search_mac_address in config_file:
            found_entry = ''.join(config_file[config_file.index(search_mac_address) - 7: config_file.index(search_mac_address) + 2])
            return True if host_entry[:-5] == found_entry else False


def check_allocation(mac_address):
    # Вернет истину если свитч в красноярском продакшине
    allocation_req = "select * from switches where switch_data @>'{\"mac\": \"" + mac_address.upper().replace(':', '-') + "\"}';"
    allocation = sql_request(allocation_req)
    if (allocation == 0) or (allocation == None):
        return False
    elif allocation[4] == 1:
        city_allocation = "select * from allocation where id={};".format(allocation[4])
        result_city = sql_request(city_allocation)
        return True if result_city[2] == 1 else False


def search_mac_address_on_config_file(mac_address):
    try:
        search_mac_address = "hardware ethernet " + mac_address.lower().replace('-', ':') + ";\n"
        with open(production_config_file) as file_handler:
            config_file = file_handler.readlines()
            return True if search_mac_address in config_file else False
    except (IOError, OSError):
        print("Error opening / processing file")


def main():
    # переключалка для ребута DHCP сервера
    dhcp_server_reboot_switch = 0
    redis_db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    try:
        response = redis_db.client_list()
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print(time.ctime(), "Connection refused - Unable to connect to Redis")
    else:
        mac_regexp = r'((?:[0-9A-F]{2}-){5}[0-9A-F]{2})'
        while True:
            time.sleep(30)  # время отдыха между циклами полного чтения Редис
            if dhcp_server_reboot_switch:
                time.sleep(5)
                reboot_dhcp_server()
                dhcp_server_reboot_switch = 0
                time.sleep(180)
            redis_all_keys = redis_db.keys()
            for keys in redis_all_keys:
                redis_current_key = keys.decode('utf-8')
                current_mac_address = re.findall(mac_regexp, redis_current_key)
                if not current_mac_address:
                    continue
                if check_allocation(current_mac_address[0]):
                    if search_mac_address_on_config_file(current_mac_address[0]):
                        if checking_for_network_settings_matches(current_mac_address[0]):
                            continue
                        else:
                            del_conf_entry(current_mac_address[0])
                            dhcp_server_reboot_switch = 1
                            continue
                    else:
                        add_conf_entry(current_mac_address[0])
                        dhcp_server_reboot_switch = 1
                        continue
                elif search_mac_address_on_config_file(current_mac_address[0]):
                    del_conf_entry(current_mac_address)
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

            # daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)
            main()
    except:
        print(time.ctime(), "Connection server - Failed")

    # else:
    #     main()
# daemon_exec(main, action, pathToPID + nameOfPID + '.pid', **out)