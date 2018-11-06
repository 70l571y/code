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


class Hostinterface:
    zapi = None

    def __init__(self):
        self.zapi = ZabbixAPI(zabbix_server)
        self.zapi.login(zabbix_username, zabbix_password)

    def get_id(self, hostid):
        params = {'hostids': [hostid]}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="hostinterface.get", params=params)['result'][0]['interfaceid']
                if get_id:
                    logging.info('Получен ID хостинтерфейса - {}!'.format(get_id))
                    return get_id
                else:
                    logging.error('Нет такого хостинтерфейса - {}'.format(hostid))
            except IndexError:
                logging.error(
                    'Ошибка при получении ID хостинтерфейса - {}'.format(hostid))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_bulk(self, hostid):
        params = {'hostids': [hostid]}
        if self.zapi:
            try:
                # get_id = self.zapi.do_request(method="hostinterface.get", params=params)['result'][0]['bulk']
                get_id = self.zapi.do_request(method="hostinterface.get", params=params)['result'][0]['bulk']
                if get_id:
                    logging.info('Получен ID хостинтерфейса - {}!'.format(get_id))
                    return get_id
                else:
                    logging.error('Нет такого хостинтерфейса - {}'.format(hostid))
            except IndexError:
                logging.error(
                    'Ошибка при получении ID хостинтерфейса - {}'.format(hostid))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def update(self, id, update_item, param):
        params = {'interfaceid': str(id), str(update_item): param}
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="hostinterface.update", params=params)
                if update_host:
                    logging.info('У хостинтерфейса {} обновлен параметр {} на {}'.format(
                        id, update_item, param))
                    return True
                else:
                    logging.error('Нет такого хостинтерфейса - {}'.format(id))
            except:
                logging.error('Ошибка при обновлении хостинтерфейса - {}'.format(id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')
