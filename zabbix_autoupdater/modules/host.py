import os
import sys
import json
import logging
from pyzabbix import ZabbixAPI, ZabbixAPIException

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


class Host:
    zapi = None

    def __init__(self):
        self.zapi = ZabbixAPI(zabbix_server)
        self.zapi.login(zabbix_username, zabbix_password)

    def create(self, host, name, proxy_hostid, global_group_id, local_group_id, template1):
        if self.zapi:
            params = {'host': host,
                      'name': name,
                      'proxy_hostid ': str(proxy_hostid),
                      'interfaces': [
                          {
                              'type': 2,
                              'main': 1,
                              'useip': 1,
                              'ip': host,
                              'dns': '',
                              'port': '161'
                          }
                      ],
                      'groups': [
                          {
                              'groupid': str(global_group_id)
                          },
                          {
                              'groupid': str(local_group_id)
                          }
                      ],
                      'templates': [
                          {
                              'templateid': str(template1)
                          }
                          # {
                          #     'templateid': str(template2)
                          # }
                      ]
                      }
            try:
                create_host_answer = self.zapi.do_request(
                    method="host.create", params=params)
                if create_host_answer:
                    logging.info('Хост {} - создан!'.format(name))
                    return create_host_answer
                else:
                    logging.error('Не могу создать хост - {}'.format(host))
            except ZabbixAPIException:
                logging.error('Ошибка при создании хоста - {}'.format(host))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def delete(self, host_id):
        params = [str(host_id)]
        if self.zapi:
            try:
                del_host = self.zapi.do_request(
                    method="host.delete", params=params)
                if del_host:
                    logging.info('Хост {} - Удален!'.format(host_id))
                    return del_host
                else:
                    logging.error('Нет такого хоста - {}'.format(host_id))
            except:
                logging.error('Ошибка при удалении хоста - {}'.format(host_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_id(self, host):
        params = {'filter': {'host': [host]}}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="host.get", params=params)[
                    'result'][0]['hostid']
                if get_id:
                    logging.info('Получен ID хоста {} - {}!'.format(host, get_id))
                    return get_id
                else:
                    logging.error('Нет такого хоста - {}'.format(host))
            except IndexError:
                logging.error(
                    'Ошибка при получении ID хоста - {}'.format(host))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_name(self, host):
        params = {'filter': {'name': [host]}}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="host.get", params=params)[
                    'result'][0]['hostid']
                if get_id:
                    logging.info('Получен name ID хоста - {}!'.format(host))
                    return get_id
                else:
                    logging.error('Нет такого хоста - {}'.format(host))
            except IndexError:
                logging.error(
                    'Ошибка при получении name ID хоста - {}'.format(host))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def update(self, id, update_item, param):
        params = {'hostid': str(id), str(update_item): str(param)}
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info('У хоста {} обновлен параметр {} на {}'.format(
                        id, update_item, param))
                    return True
                else:
                    logging.error('Нет такого хоста - {}'.format(id))
            except:
                logging.error('Ошибка при обновлении хоста - {}'.format(id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def update_two_param(self, id, update_item, param, param2):
        params = {'hostid': str(id), str(update_item): [param, param2]}
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info('У хоста {} обновлен параметр {} на {}'.format(
                        id, update_item, param))
                    logging.info('У хоста {} обновлен параметр {} на {}'.format(
                        id, update_item, param2))
                else:
                    logging.error('Нет такого хоста - {}'.format(id))
            except:
                logging.error('Ошибка при обновлении хоста - {}'.format(id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def update_many_param(self, hostid, update_item, *parameters):
        # т.к. импортирует кортеж из списка
        params = {'hostid': hostid, update_item: parameters[0]}
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info('У хоста {} обновлен параметр {} на {}'.format(
                        hostid, update_item, params['groups']))
                else:
                    logging.error('Нет такого хоста - {}'.format(hostid))
            except:
                logging.error(
                    'Ошибка при обновлении хоста - {}'.format(hostid))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def update_inventory(self, hostid, update_item, param):
        params = {'hostid': hostid, update_item: param}
        if self.zapi:
            try:
                update_host = self.zapi.do_request(method="host.update", params=params)
                if update_host:
                    logging.info('У хоста {} обновлен параметр {} на {}'.format(
                        hostid, update_item, params['groups']))
                else:
                    logging.error('Нет такого хоста - {}'.format(hostid))
            except:
                logging.error(
                    'Ошибка при обновлении инвертарных данных хоста - {}'.format(hostid))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_proxyid(self, host):
        params = {'filter': {'host': [host]}}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="host.get", params=params)
                if get_id:
                    logging.info('Получен ID хоста - {}!'.format(host))
                    return get_id['result'][0]['proxy_hostid']
                else:
                    logging.error('Нет такого хоста - {}'.format(host))
            except IndexError:
                logging.error(
                    'Ошибка при получении ID хоста - {}'.format(host))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_hostid_of_proxy(self, proxy_id):
        params = {"output": ["hostid"], "proxyids": str(proxy_id)}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="host.get", params=params)
                if get_id:
                    logging.info(
                        'Получен ID хостов от прокси - {}!'.format(proxy_id))
                    return get_id['result']
                else:
                    logging.error('У прокси {} нет хостов'.format(proxy_id))
            except IndexError:
                logging.error(
                    'Ошибка при получении хостов от прокси - {}'.format(proxy_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def get_hostid_of_template(self, template_id):
        params = {"output": ["hostid"], "templateids": str(template_id)}
        if self.zapi:
            try:
                get_id = self.zapi.do_request(method="host.get", params=params)
                if get_id:
                    logging.info(
                        'Получен ID хостов от шаблона - {}!'.format(template_id))
                    return get_id['result']
                else:
                    logging.error('У шаблона {} нет хостов'.format(template_id))
            except IndexError:
                logging.error(
                    'Ошибка при получении хостов с шаблоном - {}'.format(template_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def add_macros(self, host_id, macros, value):
        # {
        #     "jsonrpc": "2.0",
        #     "method": "host.update",
        #     "params": {
        #         "hostid": "10126",
        #         "macros": {
        #             "add": {
        #                 "{$MACRO1}": "value",
        #                 "{$MACRO2}": "5"
        #             },
        #             "delete": [
        #                 "{$MACRO4}"
        #             ],
        #             "update": {
        #                 "{$MACRO3}": "new_value"
        #             }
        #         }
        #     },
        #     "auth": "038e1d7b1735c6a5436ee9eae095879e",
        #     "id": 1
        # }

        params = {
            'hostid': str(host_id),
            'macros': {
                'add': {
                    macros: str(value)
                }
            }
        }
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info('Хосту {} добавлен макрос {} со значением {}'.format(
                        host_id, macros, value))
                    return True
                else:
                    logging.error('Нет такого хоста - {}'.format(host_id))
            except ZabbixAPIException:
                logging.error('Ошибка при обновлении хоста - {}'.format(host_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def del_macros(self, host_id, macros, value):
        params = {
            'hostid': str(host_id),
            'macros': {
                'delete': {
                    macros: str(value)
                }
            }
        }
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info('Хосту {} добавлен макрос {} со значением {}'.format(
                        host_id, macros, value))
                    return True
                else:
                    logging.error('Нет такого хоста - {}'.format(host_id))
            except ZabbixAPIException:
                logging.error('Ошибка при обновлении хоста - {}'.format(host_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def del_macros(self, host_id, macros):
        params = {
            'hostid': str(host_id),
            'macros': {
                'delete': {
                    macros
                }
            }
        }
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info('У хоста {} удален макрос {}'.format(
                        host_id, macros))
                    return True
                else:
                    logging.error('Нет такого хоста - {}'.format(host_id))
            except ZabbixAPIException:
                logging.error('Ошибка при обновлении хоста - {}'.format(host_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')

    def update_macros(self, host_id, macros, value):
        params = {
            'hostid': str(host_id),
            'macros': {
                'update': {
                    macros: str(value)
                }
            }
        }
        if self.zapi:
            try:
                update_host = self.zapi.do_request(
                    method="host.update", params=params)
                if update_host:
                    logging.info(' У хоста {} обновлен макрос {} со значением {}'.format(
                        host_id, macros, value))
                    return True
                else:
                    logging.error('Нет такого хоста - {}'.format(host_id))
            except ZabbixAPIException:
                logging.error('Ошибка при обновлении хоста - {}'.format(host_id))
                return False
        else:
            logging.info('Невозможно подключиться к Заббиксу')
