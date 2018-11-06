# Модуль для доступа к БД свтичей
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import json
import psycopg2
from modules.log import Log
from modules.config import Config


class DB:
    def __init__(self):
        self.log = Log()
        if 'postgresql' in Config.read():
            self.config = Config.read()['postgresql']
        else:
            self.log.critical('Отсутствует запись с настройками БД в файле конфига!')
            self.config = None
        self.host = self.config['host']
        self.port = self.config['port']
        self.name = self.config['name']
        self.username = self.config['username']
        self.password = self.config['password']

    def _do_request(self, sql):
        """
        запрос в БД по заданному sql запросу извне и возвращение ответа от базы
        :param sql: Сформированный sql запрос
        :return: Ответ БД
        """
        current_method = 'DB.Request'
        try:
            conn = psycopg2.connect(database=self.name, user=self.username, password=self.password, host=self.host,
                                    port=self.port)
        except psycopg2.OperationalError:
            self.log.critical('{}: Невозможно подключиться к БД ({}@{}:{})'.format(current_method, self.username,
                                                                                   self.host, self.port))
            return False
        else:
            curs = conn.cursor()
            try:
                curs.execute(sql)
            except psycopg2.Error as error:
                self.log.error(error)
                self.log.error('{}: Невозможно выполнить запрос : {}'.format(current_method, sql))
                return False
            else:
                result = curs.fetchone()
                return result

    def _do_record(self, sql):
        """
        обновление или вставка записей в базу по заданному sql
        :param sql: Сформированный sql запрос
        :return: True or False
        """
        current_method = 'DB.Request'
        try:
            conn = psycopg2.connect(database=self.name, user=self.username, password=self.password, host=self.host,
                                    port=self.port)
        except psycopg2.OperationalError:
            self.log.critical('{}: Невозможно подключиться к БД ({}@{}:{})'.format(current_method, self.username,
                                                                                   self.host, self.port))
            return False
        else:
            curs = conn.cursor()
            try:
                curs.execute(sql)
                conn.commit()
            except psycopg2.Error as error:
                self.log.error(error)
                self.log.error('{}: Невозможно выполнить запись в БД (sql: {})'.format(current_method, sql))
                return False
            else:
                return True

    def get_autoconf_switches_list(self, autoconfig_id):
        """
        Получает список свитчей для автоконфигурации из таблицы autoconfig
        :param autoconfig_id: ID текущей записи в таблице autoconfig
        :return: Список из словарей с записями из таблицы autoconfig
        """
        current_method = 'DB.get_autoconf_switches_list'

        sql = '''SELECT data 
                FROM autoconfig 
                WHERE id={};'''.format(autoconfig_id)
        result = self._do_request(sql)[0]  # Т.к. голым ответом будет list(tuple(list(dict(data))))
        if not result:
            self.log.error('{}: Невозможно получить список свитчей для автоконфигурации '
                           'из таблицы autoconfig по autoconfig_id = {}! '
                           'Или нет такого autoconfig_id в таблице autoconfig'.format(current_method, autoconfig_id))
            return False
        # переменная result должна иметь вид:
        # [{'id': 16816, 'port': 0, 'errors': [], 'status': 'waiting'},
        # {'id': 16817, 'port': 0, 'errors': [], 'status': 'waiting'},
        # {'id': 16818, 'port': 0, 'errors': [], 'status': 'waiting'},
        # {'id': 16819, 'port': 0, 'errors': [], 'status': 'waiting'}]
        return result

    def get_switch_info(self, mac, list_of_switches):
        """
        Получение информации об устройстве из пула по списку автонастройки
        :param mac: Текущий мак адрес устройства
        :param list_of_switches: Список свитчей для автонастройки
        :return: serial - строка с серийным номером
        """
        current_method = 'DB.get_switch_info'

        sql = '''
            SELECT id, switch_data
            FROM switches
            WHERE switch_data @>\'{{\"mac\": \"{}\"}}\';;
            '''.format(mac)
        switch_info = self._do_request(sql)
        # пока решил отключить ф-ию проверки имени модели get_switch_info['name']
        # (т.к. имя модели в базе, отличается от имени модели на свитче)

        if not switch_info:
            self.log.error('{}: Свитча с мак адресом "{}", нет в пуле!'.format(current_method, mac))
            return False

        switch_id = switch_info[0]
        if not switch_id:
            self.log.error('{}: В пуле у свитча: {} - отсутствует ID!'.format(current_method, self.host))
            return False

        serial = switch_info[1]['serial']
        if not serial:
            self.log.error('{}: В пуле у свитча: {} - отсутствует серийный номер!'.format(current_method, self.host))
            return False

        for line in list_of_switches:
            if switch_id == line['id']:
                return serial
        self.log.error('{}: Свитч с мак адресом {} - '
                       'отсутствует в списке автонастройки!'.format(current_method, mac))
        return False

    def get_switch_id(self, mac):
        """
        Возвращает id свитча по его mac адресу
        :return: id типа integer
        """
        current_method = 'DB.get_switch_id'

        sql = '''
        SELECT id 
        FROM switches 
        WHERE switch_data @>'{{"mac": "{}"}}';
        '''.format(mac)
        try:
            answer = self._do_request(sql)[0]
        except Exception:
        # if not answer:
            self.log.error('{}: Невозможно получить ID свитча из пула мак адресу - {}!'.format(current_method, mac))
            return False
        else:
            return answer if answer else False

    def update_autoconfig_status(self, autoconfig_id, status):
        """
        Обновляет глобальный статус автоконфига
        :param autoconfig_id: ID рабочего поля таблицы autoconfig
        :param status: Статус в текстовом формате ('working', 'error', 'done')
        """
        current_method = 'DB.update_autoconfig_status'

        sql = '''
            UPDATE autoconfig
            SET status = '{}'
            WHERE id = {};
            '''.format(status, autoconfig_id)
        try:
            self._do_record(sql)
        except Exception:
            self.log.error('{}: Невозможно обновить глобальный статус автоконфига!'.format(current_method))
            return False
        else:
            return True

    def update_autoconfig_info(self, autoconfig_id, list_switches, switch_id, **switch_entry):
        """
        Обновляет запись в таблице autoconfig.
        :param autoconfig_id: ID записи в таблице autoconfig
        :param list_switches: Список свитчей для автоконфигурации
        :param switch_id: ID текущего свитча
        :param switch_entry: Аргументы для обновления
        :return: Сформированный список с новыми аргументами
        """
        # Пример:
        # update_autoconfig_info(autoconfig_id=20, list_switches, id=16818, port=2, errors=['нет такого id'],
        # status='error')
        #
        # [{'id': 16816, 'port': 0, 'errors': [], 'status': 'waiting'},
        # {'id': 16817, 'port': 0, 'errors': [], 'status': 'waiting'},
        # {'id': 16818, 'port': 2, 'errors': ['нет такого id'], 'status': 'error'},
        # {'id': 16819, 'port': 0, 'errors': [], 'status': 'waiting'}]

        current_method = 'DB.update_autoconfig_info'

        # формируем запись для свитча в БД
        for entry in list_switches:
            if entry['id'] == switch_id:
                # switch_entry может содержать только 3 аргумента: port, errors, status
                # причем errors это список из ошибок (т.к. ошибка может быть не одна)
                for item in switch_entry:
                    # на всякий случай обработаем только нужные нам аргументы
                    if item == 'errors':
                        entry['errors'].append(switch_entry[item])
                        continue
                    elif item == 'port':
                        entry[item] = switch_entry[item]
                    elif item == 'status':
                        entry[item] = switch_entry[item]

        sql = '''
          UPDATE autoconfig
          SET data='{data}'
          WHERE id={id};
          '''.format(data=json.dumps(list_switches), id=autoconfig_id)
        try:
            self._do_record(sql)
        except Exception:
            self.log.error('{}: Невозможно обновить запись в таблице autoconfig!'.format(current_method))
            return False
        else:
            return True

    def checking_the_last_run(self):
        """
        Проверяет аварийное завершение работы агента во время автоконфига
        В случае если прошлый запуск агента завершился аварийно (т.е. статус будет - waiting) -
        переводит глобальный статус таблицы autoconfig в "error"
        :return: True or False
        """
        current_method = 'DB.checking_the_last_run'

        sql = '''
        select * 
        from autoconfig 
        where status not in ('done', 'error');
        '''
        try:
            answer = self._do_request(sql)
        except:
            self.log.info('{}: Предыдущий запуск автоконфигурации аварийно завершился!'.format(current_method))
            self.log.info('{}: Устанавливаю глобальный статус автоконфига - error!'.format(current_method))
            autoconfig_id = answer[0]  # получаем кортеж, первый элемент которого это id
            success = self.update_autoconfig_status(autoconfig_id, 'error')
            if not success:
                self.log.error('{}: Невозможно обновить глобальный статус автоконфига!'.format(current_method))
