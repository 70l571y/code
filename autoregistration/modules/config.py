# Модуль парсит конфиг-файл с настройками автоконфигуратора
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import os
import sys
import yaml
from modules.log import Log

# Путь до конфиг файла по умолчанию
PATH = '/opt/autoregistration/config.yaml'


class Config:
    """
    Класс включающие метод по чтению конфига
    """
    log = Log()

    @staticmethod
    def _create_config():
        """
        Метод создает чистый конфиг с настройками по умолчанию!
        """

        # Заполняем конфиг параметрами по умолчанию
        data = {
            'postgresql': {
                'host': 'swdb3.krk.orionnet.ru',
                'port': 5432,
                'name': 'switchbase',
                'username': 'WRITE USERNAME',
                'password': 'WRITE PASSWORD'
            },
            'switch': {
                'login': 'WRITE LOGIN',
                'password': 'WRITE PASSWORD'
            },
            'rabbit': {
                'host': 'swdb3.krk.orionnet.ru',
                'port': 5672,
                'queue': 'autoconfig',
                'username': 'WRITE USERNAME',
                'password': 'WRITE PASSWORD',
                'exchange': 'autoconfig',
                'exchange_type': 'fanout'
            },
            'redis': {
                'db': 0,
                'host': 'localhost',
                'port': 6379,
                'password': 'WRITE PASSWORD'
            },
            'registrar': {
                'ip': '192.168.183.52'
            }
        }

        # Пишем конфиг в файл
        with open(PATH, 'w') as config_file:
            yaml.dump(data, config_file, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def read():
        """
        Метод читает данные из конфиг-файла
        :return Структура конфига
        """

        if os.path.exists(PATH):
            return yaml.load(open(PATH))
        Config.log.critical('Отсутствует файл лога!')
        Config._create_config()
        Config.log.critical('Файл лога создан с параметрами по умолчанию: {}'.format(PATH))
        Config.log.critical('Заполните необходимые параметры и перезапустите приложение!')
        sys.exit()
