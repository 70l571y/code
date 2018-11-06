# Модуль получаем информацию с DHCP сервера
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import redis
from modules.log import Log
from modules.config import Config


class DHCP:
    def __init__(self):
        self.log = Log()
        if 'redis' in Config.read():
            self.config = Config.read()['redis']
        else:
            self.log.critical('Отсутствует запись с настройками Redis в файле конфига!')
            self.config = None
        self.host = self.config['host']
        self.password = self.config['password']
        self.port = self.config['port']
        self.db = self.config['db']

    def get_ip(self, mac):
        """
        По MAC адресу запрашивает у DHCP текущий IP адрес оборудования;
        :return:
        """
        current_function = 'DHCP.Get_IP'

        redis_db = redis.StrictRedis(host=self.host,
                                     password=self.password,
                                     port=self.port,
                                     db=self.db)
        try:
            response = redis_db.client_list()  # Да, переменную "response" обязательно нужно создать!
            # Проверка есть ли коннект с БД Redis
        except (redis.exceptions.ConnectionError, ConnectionRefusedError):
            self.log.critical('{}: Невозможно подключиться в БД Redis ({}:{}, db{})'.format(current_function, self.host,
                                                                                            self.port, self.db))
            return False
        else:
            current_ip = redis_db.get(mac)
            if current_ip is None:
                self.log.error('{}: Невозможно получить IP по мак адресу - {}. '
                               'Или нет записи в БД Редис с таким мак адресом'.format(current_function, mac))
                return False
            current_ip = current_ip.decode('utf-8')
            return current_ip
