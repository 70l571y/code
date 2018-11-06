# Модуль считавает сообщения от кролика (RabbitMQ) на запуск процесса автонастройки
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import json
import pika
from modules.log import Log
from modules.config import Config

class RabbitMessageChecker:
    connection = None
    delivery_tag = 0  # Если равен 1, то кролик получил сообщение!
    message = None

    def __init__(self):
        self.log = Log()
        if 'rabbit' in Config.read():
            self.config = Config.read()['rabbit']
        else:
            self.log.critical('Отсутствует запись с настройками RabbitMQ в файле конфига!')
            self.config = None

        self.host = self.config['host']
        self.port = self.config['port']
        self.username = self.config['username']
        self.password = self.config['password']
        self.exchange = self.config['exchange']
        self.exchange_type = self.config['exchange_type']

        cred = pika.PlainCredentials(self.username, self.password)
        params = pika.ConnectionParameters(host=self.host,
                                           port=self.port,
                                           virtual_host='/',
                                           credentials=cred)
        self.connection = pika.BlockingConnection(params)

    def run(self):
        def check_queue(ch, method, properties, body):
            try:
                # Получаем сообщение от кролика формата: {"type":"autoconfig_start","data":{"id":1}}
                self.message = json.loads(body.decode('utf-8'))  # По умолчанию принимает строку в бинарном формате
            except ValueError as not_json:
                # Если кролик передаст строку не в json формате
                self.log.critical('Некорректное сообщение от кролика: {}. '
                                  'Сообщение должно быть в JSON формате!'.format(not_json))
            else:
                self.delivery_tag = 1
                self.connection.close()

        if self.connection:
            channel = self.connection.channel()
            channel.exchange_declare(exchange=self.exchange,
                                     exchange_type=self.exchange_type)
            result = channel.queue_declare(exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange=self.exchange,
                               queue=queue_name)

            channel.basic_consume(check_queue,
                                  queue=queue_name,
                                  no_ack=True)
            try:
                channel.start_consuming()
            except pika.exceptions.ConnectionClosed:
                self.log.critical('Нет соединения с кроликом '
                                  '({}@{}:{}, ex: {}, ex type: {})!'.format(self.username, self.host,  self.port,
                                                                            self.exchange, self.exchange_type))
