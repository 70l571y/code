#!/usr/bin/python3
import os
import sys
import json
import math
import logging
import paramiko
import itertools
import subprocess
from time import sleep
from threading import Thread
from modules.host import Host
from modules.group import Group
from modules.db import DB
from modules.hostinterface import Hostinterface
from pyzabbix import ZabbixAPIException
from ipaddress import ip_address, ip_interface

DIR = '/root/app/zabbix_autoupdater/'

NEW_FILE = DIR + 'files/new/zabbix_sync.csv'
OLD_FILE = DIR + 'files/old/zabbix_sync.csv'
UPS_FILE = DIR + 'config/ups.txt'
ADDING_FILE = DIR + 'files/adding.csv'
CONFIG_FILE = DIR + 'config/config.json'
DELETING_FILE = DIR + 'files/deleting.csv'
CTV_MODEL_FILE = DIR + 'config/ctv.txt'
AGREGATION_FILE = DIR + 'config/agregations.txt'
SUBNETWORKS_FILE = DIR + 'config/subnetworks.json'
SYNC_FILE_REMOTHE_PATH = '/tmp/zabbix_sync.csv'
CAMERAS_MODEL_FILE = DIR + 'config/cameras.txt'
SWITCHES_MODEL_FILE = DIR + 'config/commutators.txt'
SNMP_TEMPLATES_FILE = DIR + 'config/snmp_templates.json'
SYNC_FILE_LOCAL_PATH = DIR + 'files/new/zabbix_sync.csv'
TELEPHONES_MODEL_FILE = DIR + 'config/telephones.txt'
NO_SNMP_BULK_LIST_MODEL_FILE = DIR + 'config/no_snmp_bulk.txt'

# Заргужаем основной конфиг
with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

# Загружаем файл ID SNMP шаблонов
with open(SNMP_TEMPLATES_FILE) as f:
    LIST_OF_SNMP_TEMPLATES = json.load(f)

sys.path.append('..')
LOG_PATH = '/var/log/zabbix-scripts/'
LOG_NAME = 'autoupdater'

if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.INFO,
                    filename=u'{}{}.log'.format(LOG_PATH, LOG_NAME))
logging.info('\n')  # Отделять логи пустой строкой

REMOTE_FTP_SERVER_HOSTNAME = CONFIG['ftp_server']
REMOTE_FTP_SERVER_USERNAME = CONFIG['ftp_username']
REMOTE_FTP_SERVER_PASSWORD = CONFIG['ftp_password']

SWDB = DB()
ZABBIX_HOST = Host()
ZABBIX_GROUP = Group()
ZABBIX_HOSTINTERFACE = Hostinterface()

ABK_PROXY_ID = CONFIG['abk_proxyid']
BRK_PROXY_ID = CONFIG['brk_proxyid']
# irk_proxyid = config['irk_proxyid']
KNS_PROXY_ID = CONFIG['kns_proxyid']
KRK_PROXY_ID = CONFIG['krk_proxyid']


def download_file():
    # Загрузка файла выгрузки СВДБ с удаленного фтп сервера
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(REMOTE_FTP_SERVER_HOSTNAME, username=REMOTE_FTP_SERVER_USERNAME,
                    password=REMOTE_FTP_SERVER_PASSWORD)
    except paramiko.ssh_exception.NoValidConnectionsError:
        logging.info('Невозмжоно подключиться к серверу {}'.format(
            REMOTE_FTP_SERVER_HOSTNAME))
        ssh.close()
        return False
    sftp = ssh.open_sftp()
    try:
        logging.info('Загрузка файла с удаленного сервера {}...'.format(
            REMOTE_FTP_SERVER_HOSTNAME))
        sftp.get(SYNC_FILE_REMOTHE_PATH, SYNC_FILE_LOCAL_PATH)
        sleep(3)
        logging.info(
            'Файла с удаленного сервера {} - загружен!'.format(REMOTE_FTP_SERVER_HOSTNAME))
    except FileNotFoundError:
        logging.info('Нет файла на сервере')
        return False
    sftp.close()
    ssh.close()
    return True


def create_hosts_files():
    # Формирование файлов на добавления и удаления хостов из заббикса
    try:
        with open(NEW_FILE) as new_file:
            new_data = new_file.readlines()
    except FileNotFoundError:
        logging.error('Ошибка при открытии файла {}'.format(NEW_FILE))
        return False
    else:
        try:
            with open(OLD_FILE) as old_file:
                old_data = old_file.readlines()
        except FileNotFoundError:
            logging.error('Ошибка при открытии файла {}'.format(OLD_FILE))
            return False
        else:
            # Формируем файл на добавление новых хостов в Заббикс
            # Очищаем файл
            with open(ADDING_FILE, 'w') as adding_file:
                adding_file.write('')
            for row in new_data:
                if 'Красноярск,' in row:
                    if row not in old_data:
                        # Добавляем уникальные строки в новый файл
                        with open(ADDING_FILE, 'a') as adding_file:
                            adding_file.write(row)
                elif 'Абакан,' in row:
                    if row not in old_data:
                        # Добавляем уникальные строки в новый файл
                        with open(ADDING_FILE, 'a') as adding_file:
                            adding_file.write(row)
                elif 'Братск,' in row:
                    if row not in old_data:
                        # Добавляем уникальные строки в новый файл
                        with open(ADDING_FILE, 'a') as adding_file:
                            adding_file.write(row)
                # elif 'Иркутск,' in row:
                #     if row not in old_data:
                #         # Добавляем уникальные строки в новый файл
                #         with open(ADDING_FILE, 'a') as adding_file:
                #             adding_file.write(row)
                elif 'Канск,' in row:
                    if row not in old_data:
                        # Добавляем уникальные строки в новый файл
                        with open(ADDING_FILE, 'a') as adding_file:
                            adding_file.write(row)

            # Формируем файл на удаление новых хостов в Заббикс
            # Очищаем файл
            with open(DELETING_FILE, 'w') as deleting_file:
                deleting_file.write('')
            for row in old_data:
                if 'Красноярск,' in row:
                    if row not in new_data:
                        # Добавляем уникальные строки в новый файл
                        with open(DELETING_FILE, 'a') as deleting_file:
                            deleting_file.write(row)
                elif 'Абакан,' in row:
                    if row not in new_data:
                        # Добавляем уникальные строки в новый файл
                        with open(DELETING_FILE, 'a') as deleting_file:
                            deleting_file.write(row)
                elif 'Братск,' in row:
                    if row not in new_data:
                        # Добавляем уникальные строки в новый файл
                        with open(DELETING_FILE, 'a') as deleting_file:
                            deleting_file.write(row)
                # elif 'Иркутск,' in row:
                #     if row not in new_data:
                #         # Добавляем уникальные строки в новый файл
                #         with open(DELETING_FILE, 'a') as adding_file:
                #             adding_file.write(row)
                elif 'Канск,' in row:
                    if row not in new_data:
                        # Добавляем уникальные строки в новый файл
                        with open(DELETING_FILE, 'a') as deleting_file:
                            deleting_file.write(row)
    logging.info('Файлы на добавление и удаление устройств сформированы!')
    return True


def delete_hosts(filepath):
    # Удаление списка хостов из файла files/old/zabbix_sync.csv
    if os.path.isfile(filepath):
        with open(filepath) as file:
            lines = file.readlines()
            if lines:
                for row in lines:
                    ip = row.rstrip().split(',')[0]
                    while True:  # На случай, если будет разрыв соединения с заббиксом
                        try:
                            hostid = ZABBIX_HOST.get_id(str(ip).rstrip())
                            ZABBIX_HOST.delete(hostid)
                        except ZabbixAPIException:
                            sleep(10)
                            continue
                        else:
                            break
                    logging.info('Хост {} - удален'.format(row.split(',')[2]))
            else:
                logging.error('Файл "{}" пуст!'.format(filepath))
                file.close()
    else:
        logging.error('Файл "{}" отсутствует'.format(filepath))


def get_agregation_group(host):
    # Получение название группы узла агрегации, к которому принадлежит данный хост
    # Заргужаем файл со списком подсетей
    with open(SUBNETWORKS_FILE) as file:
        subnetworks = json.load(file)

    for agregation in subnetworks:
        interfaces = subnetworks[agregation]
        for interface in interfaces:
            ipif = ip_interface(interface)
            network = ipif.network
            ipaddr = ip_address(host)
            if ipaddr in network:
                return agregation
    return False


def update_all_groups(host, model, global_groupid, local_groupid):
    # Обновление/добавление всех групп, к которым принадлежит/должен принадлежать данный хост
    # У хостов в заббиксе от 3 до 4-х групп
    groups = []  # Имя всех групп, которые необходимо добавить хосту
    groupids = []  # ID всех групп, которые необходимо добавить хосту

    # Загружаем файл моделей, которые входят в группу Агрегация
    if model in open(AGREGATION_FILE).read():
        groups.append('Агрегация')

    # Загружаем файл моделей, которые входят в группу ИБП
    if model in open(UPS_FILE).read():
        groups.append('ИБП')

    # Загружаем файл моделей, которые входят в группу Коммутаторы
    if model in open(SWITCHES_MODEL_FILE).read():
        groups.append('Коммутаторы')

    # Загружаем файл моделей, которые входят в группу КТВ
    if model in open(CTV_MODEL_FILE).read():
        groups.append('КТВ')

    # Загружаем файл моделей, которые входят в группу Камеры
    if model in open(CAMERAS_MODEL_FILE).read():
        groups.append('Камеры')

    # Загружаем файл моделей, которые входят в группу Телефония
    if model in open(TELEPHONES_MODEL_FILE).read():
        groups.append('Телефония')

    ag_group = get_agregation_group(host)

    if ag_group:
        groups.append(ag_group)

    groupids.append(int(global_groupid))
    groupids.append(int(local_groupid))

    # Получаем id групп по текущим именам
    for group in groups:
        groupid = ZABBIX_GROUP.get_id(group)
        if groupid:
            groupids.append(int(groupid))

    hostid = ZABBIX_HOST.get_id(host)
    ZABBIX_HOST.update_many_param(hostid, 'groups', groupids)


def check_no_snmp_bulk(host, model):
    # Некоторым моделям оборудования необходимо отключить массовые запросы
    # SNMP (железки зависают)
    if model in open(NO_SNMP_BULK_LIST_MODEL_FILE).read():
        hostid = ZABBIX_HOST.get_id(host)
        hostifid = ZABBIX_HOSTINTERFACE.get_id(hostid)
        ZABBIX_HOSTINTERFACE.update(hostifid, "bulk", 0)
    else:
        return False


def create_hosts_handler(lines):
    while True:  # На случай, если будет разрыв соединения с заббиксом
        try:
            abk_groupid = ZABBIX_GROUP.get_id('Абакан')
            brk_groupid = ZABBIX_GROUP.get_id('Братск')
            # irk_groupid = zabbix_group.get_id('Иркутск')
            kns_groupid = ZABBIX_GROUP.get_id('Канск')
            krk_groupid = ZABBIX_GROUP.get_id('Красноярск')
        except ZabbixAPIException:
            sleep(10)
            continue
        else:
            break

    for line in lines:
        if 'Красноярск,' in line:  # В конце названия города, явно поставить запятую!!!
            proxy_hostid = KRK_PROXY_ID[-1]
            global_groupid = krk_groupid
            macros_city = 'Крк'
        elif 'Абакан,' in line:
            proxy_hostid = ABK_PROXY_ID
            global_groupid = abk_groupid
            macros_city = 'Абк'
        elif 'Братск,' in line:
            proxy_hostid = BRK_PROXY_ID[0]
            global_groupid = brk_groupid
            macros_city = 'Брк'
        # elif 'Иркутск,' in line:
        #     proxy_hostid = irk_proxyid[0]
        #     global_groupid = irk_groupid
        #     macros_city = 'Ирк'
        elif 'Канск,' in line:
            proxy_hostid = KNS_PROXY_ID[0]
            global_groupid = kns_groupid
            macros_city = 'Кнс'
        else:
            continue

        string = line.rstrip().split(',')
        switch_id = string[0]
        host = string[1]
        city = string[2]
        address = string[3]
        model = string[4]
        mac = string[5]
        comment = SWDB.get_switch_comment(switch_id)
        serial = string[6] if len(string) > 6 else ""

        name = city + ': ' + address
        counter = 0
        create_answer = ''
        inventory_param = {}
        icmp_param = {}
        snmp_param = {}

        local_groupname = city + ' ' + address

        if mac:
            inventory_param['macaddress_a'] = mac
        if serial:
            inventory_param['serialno_a'] = serial
        if model:
            inventory_param['model'] = model

        # в этикетку (host inventory) прописываем id свитчей
        inventory_param['asset_tag'] = switch_id

        inventory_param['url_a'] = 'http://swdb3.krk.orionnet.ru/device?id=' + str(switch_id) + '#topo'

        while True:  # На случай, если будет разрыв соединения с заббиксом
            try:
                local_groupid = ZABBIX_GROUP.get_id(local_groupname)
                if not local_groupid:  # если нет локальной группы, то создадим ее
                    ZABBIX_GROUP.create(local_groupname)
                    local_groupid = ZABBIX_GROUP.get_id(local_groupname)

                # Проверяем есть ли уже такое имя хоста
                host_id = ZABBIX_HOST.get_id(host)

                if host_id:
                    # Добавляем/обновляем все группы у хоста
                    update_all_groups(
                        host, model, global_groupid, local_groupid)

                    # Добавляем макрос города
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.CITY}', macros_city)

                    # Добавляем/обновляем хосты, у которых нужно отключить
                    # массовые запросы по SNMP
                    check_no_snmp_bulk(host, model)

                    # Добавляем хосту параметр proxy_hostid
                    ZABBIX_HOST.update(host_id, 'proxy_hostid', proxy_hostid)

                    # Добавляем/обновляем хосту мак адерс, модель и серйиный
                    # номер
                    ZABBIX_HOST.update_inventory(host_id, 'inventory_mode', 0)
                    ZABBIX_HOST.update_inventory(
                        host_id, 'inventory', inventory_param)

                    # Добавляем макрос географического адреса хоста
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.SITE.ADDRESS.A}', address)

                    # Добавляем макрос комментариев к хосту
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.SITE.ADDRESS.B}', comment)

                    # Добавляем макрос модели
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.MODEL}', model)

                    # Добавляем SNMP шаблон устройству
                    if model in LIST_OF_SNMP_TEMPLATES:
                        icmp_param['templateid'] = CONFIG['icmp_template']
                        snmp_param[
                            'templateid'] = LIST_OF_SNMP_TEMPLATES[model]
                        ZABBIX_HOST.update_two_param(
                            host_id, 'templates', icmp_param, snmp_param)
                else:
                    create_answer = ZABBIX_HOST.create(host, name, proxy_hostid, global_groupid, local_groupid,
                                                       CONFIG['icmp_template'])
                    # Добавляем макрос города
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.CITY}', macros_city)
                    # Добавляем макрос географического адреса хоста
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.SITE.ADDRESS.A}', address)
                    # Добавляем макрос комментариев к хосту
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.SITE.ADDRESS.B}', comment)
                    # Добавляем макрос модели
                    ZABBIX_HOST.add_macros(host_id, '{$_INVENTORY.MODEL}', model)

                    if not create_answer:
                        counter += 1
                        name = city + ': ' + address + '_' + str(counter)

                        # Кол-во хостов в 1 ТКД (чтобы приложение не ушло в
                        # бесконечный цикл)
                        number_of_hosts = CONFIG[
                            'number_of_hosts_at_one_tkd']  # 1000 хостов по умолчанию
                        if counter == number_of_hosts:  # вдруг железок будет очень много
                            break
                        logging.info(
                            'Уже есть такое имя хоста - {}'.format(name))
                        continue
            except ZabbixAPIException:
                sleep(10)
                continue
            else:
                break

        if create_answer:
            while True:  # На случай, если будет разрыв соединения с заббиксом
                try:
                    # Обновляем все группы у хоста (на всякий случай)
                    update_all_groups(
                        host, model, global_groupid, local_groupid)

                    # Добавляем хосты, у которых нужно отключить массовые
                    # запросы по SNMP
                    check_no_snmp_bulk(host, model)

                    host_id = ZABBIX_HOST.get_id(host)
                    # Добавляем хосту параметр proxy_hostid
                    ZABBIX_HOST.update(host_id, 'proxy_hostid', proxy_hostid)
                    # Добавляем хосту мак адерс, модель и серйиный номер
                    ZABBIX_HOST.update_inventory(host_id, 'inventory_mode', 0)
                    ZABBIX_HOST.update_inventory(
                        host_id, 'inventory', inventory_param)

                    # Добавляем SNMP шаблон устройству
                    if model in LIST_OF_SNMP_TEMPLATES:
                        icmp_param['templateid'] = CONFIG['icmp_template']
                        snmp_param[
                            'templateid'] = LIST_OF_SNMP_TEMPLATES[model]
                        ZABBIX_HOST.update_two_param(
                            host_id, 'templates', icmp_param, snmp_param)
                except ZabbixAPIException:
                    sleep(10)
                    continue
                else:
                    break
        else:
            logging.error(
                'Хост {} - {} - не может быть добавлен!'.format(host, name))
    else:
        logging.info('Все хосты добавлены')


def create_hosts(filepath):
    end = 0
    # кол-во устройств, которые обработает каждый поток
    devices_in_thread = CONFIG['devices_in_thread']

    if os.path.isfile(filepath):
        with open(filepath) as file:
            lines = file.readlines()
            if lines:
                if len(lines) > devices_in_thread:
                    threads_count = math.ceil(len(lines) / devices_in_thread)
                    for i in range(int(threads_count)):
                        start = end
                        end += devices_in_thread
                        split_lines = itertools.islice(lines, start, end)
                        thread = Thread(
                            target=create_hosts_handler, args=(split_lines,))
                        thread.start()
                else:
                    create_hosts_handler(lines)
            else:
                logging.error('Файл "{}" пуст!'.format(filepath))
                file.close()
    else:
        logging.error('Файл "{}" отсутствует'.format(filepath))


def move_proxyid(move_proxyid_from, move_proxyid_to, count):
    counter = 0
    errors = []

    print()
    print('Поиск хостов на прокси {} ...'.format(move_from))
    print('---')
    while True:  # На случай, если будет разрыв соединения с заббиксом
        try:
            # список id хостов, которые висят на опр. прокси, вида -
            # [{'hostid': '15352'}, {'hostid': '15413'}...]
            host_ids = ZABBIX_HOST.get_hostid_of_proxy(move_proxyid_from)
            if host_ids:
                if len(host_ids) < count:
                    print('Внимание! Колличество хостов с прокси - {} '
                          'меньше чем кол-во хостов для переноса - {}'.format(move_proxyid_from, count))
                    sleep(1)
                    print('Перемещаем все хосты с прокси {} '
                          'на прокси {} через 10 секунд...!'.format(move_proxyid_from, move_proxyid_to))
                    sleep(10)

                for line in host_ids:
                    if counter == count:
                        print('Все хосты добавлены!')
                        if errors:
                            print('Не удалось обновить proxyid у хостов:')
                            for host in errors:
                                print(host)
                        break
                    host_id = line['hostid']
                    answer = ZABBIX_HOST.update(
                        host_id, 'proxy_hostid', move_proxyid_to)
                    if answer:
                        print(
                            'Изменен параметр у хоста {} - {} из {}'.format(host_id, counter + 1, count))
                        counter += 1
                    else:
                        print('Не обновлен параметр у хоста {}'.format(host_id))
                        errors.append(host_id)
                break
        except ZabbixAPIException:
            sleep(10)
            continue
        else:
            break


def clear_icmp_template(template_id, host_id=False):
    counter = 0
    errors = []

    if not host_id:
        print()
        print('Поиск хостов c шаблоном {} ...'.format(template_id))
        print('---')
        while True:  # На случай, если будет разрыв соединения с заббиксом
            try:
                # список id хостов, которые висят на опр. шаблоне, вида -
                # [{'hostid': '15352'}, {'hostid': '15413'}...]
                host_ids = ZABBIX_HOST.get_hostid_of_template(template_id)
                if host_ids:
                    for line in host_ids:
                        host_id_line = line['hostid']
                        param = dict()
                        param['templateid'] = str(template_id)
                        answer = ZABBIX_HOST.update(
                            host_id_line, 'templates_clear', param)
                        if answer:
                            counter += 1
                            print('Отсоединен шаблон у хоста {} - {} из {}'.format(host_id_line, counter, len(host_ids)))
                        else:
                            print('Не обновлен параметр у хоста {}'.format(host_id_line))
                            errors.append(host_id_line)
                    break
            except ZabbixAPIException:
                sleep(10)
                continue
        sys.exit(2)

    # Убираем шаблон у конкретного узла
    param = dict()
    param['templateid'] = str(template_id)
    answer = ZABBIX_HOST.update(host_id, 'templates_clear', param)
    if answer:
        print('Отсоединен шаблон {} у хоста {}'.format(template_id, host_id))
    else:
        print('Не обновлен параметр у хоста {}'.format(host_id))
        errors.append(host_id)


def main():
    if download_file():
        if create_hosts_files():
            delete_hosts(DELETING_FILE)
            create_hosts(ADDING_FILE)

            # Перемещение нового файла в папку files/old
            logging.info('Перемещение нового файла в папку files/old')
            return_code = subprocess.call(['mv', NEW_FILE, OLD_FILE])
            if not return_code:
                logging.info('Новый файл успешно перемещен в папку files/old')
            else:
                logging.info(
                    'Ошибка при перемещении файла {} в папку files/old'.format(NEW_FILE[-15:]))

            # Удаление неиспользованных файлов (на удаление и на добавление)
            # return_code = subprocess.call(['rm', ADDING_FILE])
            # if not return_code:
            #     logging.info('Новый файл успешно перемещен в папку files/old')
            # else:
            #     logging.info('Ошибка при удалении файла {}'.format(ADDING_FILE[-10:]))
            #
            # return_code = subprocess.call(['rm', DELETING_FILE])
            # if not return_code:
            #     logging.info('Новый файл успешно перемещен в папку files/old')
            # else:
            #     logging.info('Ошибка при удалении файла {}'.format(DELETING_FILE[-12:]))


if __name__ == '__main__':
    if 1 < len(sys.argv) <= 5:
        if 'update' == sys.argv[1]:
            download_file()
            create_hosts(NEW_FILE)
            sys.exit(2)
        if 'move' == sys.argv[1]:
            if len(sys.argv) == 5:
                move_from = sys.argv[2]
                move_to = sys.argv[3]
                number_of_devices = int(sys.argv[4])
                move_proxyid(move_from, move_to, number_of_devices)
                sys.exit(2)
            else:
                print('Проверьте кол-во аргументов')
        if 'clear_template' == sys.argv[1]:
            if len(sys.argv) == 4:
                clear_icmp_template(sys.argv[2], sys.argv[3])
                sys.exit(2)
            clear_icmp_template(sys.argv[2])
            sys.exit(2)
        if 'help' == sys.argv[1] or '-h' == sys.argv[1]:
            print('''
                Справка по аргументам командной строки:

            update
                Обновление/добавление всех девайсов с выгрузки БД

            move [move_proxyid_from, move_proxyid_to, count]
                Перемещение устройств из одного прокси, в другой

            clear_template [template_id] [host_id]
                Отсоединить шаблон от хоста. Если не указан хост (host ID),
                то отсоединить от всех хостов с заббикса.
                Например: clear_template 10307 24085
                          clear_template 1037

            Без аргументов
                Синхронизация устройств с БД SWDB и БД Zabbix
                ''')
        else:
            print("Неизвестная команда")
            sys.exit(2)
    else:
        main()
        sys.exit(2)
