# Модуль для доступа к БД свтичей
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import json
import psycopg2


class DB:
    DIR = '/root/app/zabbix_autoupdater/'
    CONFIG_FILE = DIR + 'config/config.json'
    
    def __init__(self):
        # Заргужаем основной конфиг
        with open(self.CONFIG_FILE) as f:
            config = json.load(f)
            
        self.host = config['db_host']
        self.port = config['db_port']
        self.name = config['db_name']
        self.username = config['db_username']
        self.password = config['db_password']

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
            print('{}: Невозможно подключиться к БД ({}@{}:{})'.format(current_method, self.username,
                                                                                   self.host, self.port))
            return False
        else:
            curs = conn.cursor()
            try:
                curs.execute(sql)
            except psycopg2.Error as error:
                print(error)
                print('{}: Невозможно выполнить запрос : {}'.format(current_method, sql))
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
            print('{}: Невозможно подключиться к БД ({}@{}:{})'.format(current_method, self.username,
                                                                                   self.host, self.port))
            return False
        else:
            curs = conn.cursor()
            try:
                curs.execute(sql)
                conn.commit()
            except psycopg2.Error as error:
                print(error)
                print('{}: Невозможно выполнить запись в БД (sql: {})'.format(current_method, sql))
                return False
            else:
                return True

    def get_switch_comment(self, switch_id):
        """
        Получение комментария у свитча (где описывается место размещения, контакты и т.д.) из БД SWDB
        :param mac: Текущий мак адрес устройства
        :return: serial - строка с серийным номером
        """
        current_method = 'DB.get_switch_info'

        sql = '''
            SELECT id, switch_data
            FROM switches
            WHERE id='{}';
            '''.format(switch_id)
        switch_info = self._do_request(sql)

        if not switch_info:
            print('{}: Свитча с ID "{}", нет в пуле!'.format(current_method, switch_id))
            return False
        # TODO сделать возврат именно коммента свитча

        return False
