import os
import sys
import json
import logging
from pyzabbix import ZabbixAPI

DIR = '/root/app/zabbix_autoupdater/'

with open(DIR + 'config/config.json') as f:
    config = json.load(f)

sys.path.append('..')
LOG_PATH = '/var/log/zabbix-scripts/'
LOG_NAME = 'autoupdater'

if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s',
                    level=logging.INFO,
                    filename=u'{}{}.log'.format(LOG_PATH, LOG_NAME))

zabbix_server = config['zabbix_server']
zabbix_username = config['zabbix_username']
zabbix_password = config['zabbix_password']


class Group:
    zapi = None

    def __init__(self):
        self.zapi = ZabbixAPI(zabbix_server)
        self.zapi.login(zabbix_username, zabbix_password)

    def create(self, name):
        params = {'name': name}
        if self.zapi:
            try:
                create_group = self.zapi.do_request(
                    method="hostgroup.create", params=params)
                if create_group:
                    logging.info('Группа {} - создана!'.format(name))
                    return create_group
                else:
                    logging.error('Невозможно создать группу - {}!'.format(name))
            except:
                logging.error('Ошибка при создании группы - {}!'.format(name))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_id(self, group_name):
        params = {'output': 'extend', 'filter': {'name': [group_name], }}
        if self.zapi:
            try:
                groupid = self.zapi.do_request(method="hostgroup.get", params=params)
                if groupid:
                    logging.info('Получен ID группы: {}!'.format(group_name))
                    return groupid['result'][0]['groupid']
                else:
                    logging.error('Нет такой группы - {}!'.format(group_name))
            except:
                logging.error('Не могу получить ID группы - {}!'.format(group_name))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_groupid(self, host):
        params = {
            "output": ["hostid"],
            "selectGroups": "extend",
            'filter': {
                'host': [host]}}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="host.get", params=params)
                if get_id:
                    logging.info('Получен ID хоста - {}!'.format(host))
                    return get_id['result'][0]['groups']
                else:
                    logging.error('Нет такого хоста - {}'.format(host))
            except IndexError:
                logging.error('Ошибка при получении ID хоста - {}'.format(host))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_all(self):
        if self.zapi:
            try:
                groups = self.zapi.hostgroup.get(output=['itemid', 'name'])
                if groups:
                    logging.info('Получен список всех групп')
                    return groups
                else:
                    logging.info('Список всех групп не получен')
            except:
                logging.info('Невозможно получить список всех групп')
        else:
            logging.info('Невозможно подключиться к Заббиксу')
