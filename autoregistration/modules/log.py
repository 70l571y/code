# Модуль записывает сообщения в лог файл
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import os
import sys
import logging


class Log:
    def __init__(self):
        sys.path.append('..')
        directory = '/tmp/autoregistration/daemons/'
        filename = 'agent'

        if not os.path.exists(directory):
            os.makedirs(directory)

        logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s',
                            level=logging.INFO,
                            filename=u'{}{}.log'.format(directory, filename))

    @staticmethod
    def info(msg):
        logging.info(msg)

    @staticmethod
    def error(msg):
        logging.error(msg)

    @staticmethod
    def critical(msg):
        logging.critical(msg)
