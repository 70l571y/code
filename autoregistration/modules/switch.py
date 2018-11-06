# Модуль для управления коммутаторами
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304
import telnetlib
from time import sleep
from modules.log import Log
from modules.config import Config
from subprocess import Popen, PIPE
from easysnmp import snmp_walk, snmp_set, snmp_get, exceptions


class Switch:
    # Команды коммутатора
    SHOW_INFO = 'show switch'  # Показать информацию о свитче (D-Link)
    ENABLE_DHCP_CLIENT = 'config ipif System dhcp'  # Активация dhcp client на оборудовании
    DEVICE_REBOOT = 'reboot force_agree'  # Перезагрузка оборудования
    ENABLE_AUTOIMAGE = 'enable autoimage'  # Включение автопрошивки
    DISABLE_AUTOIMAGE = 'disable autoimage'  # Отключение автопрошивки
    ENABLE_AUTOCONFIG = 'enable autoconfig'  # Включение автоконфигурации
    DISABLE_AUTOCONFIG = 'disable autoconfig'  # Отключение автоконфигурации
    SAVING_SETTINGS = 'save'  # Сохранение настроек

    def __init__(self, host):
        self.host = host
        self.log = Log()
        if 'switch' in Config.read():
            self.config = Config.read()['switch']
        else:
            self.log.critical('Отсутствует запись с настройками Switch в файле конфига!')
            self.config = None

    def ping(self):
        """
        Отправляет запросы (ICMP Echo-Request) протокола ICMP указанному свитчу
            и фиксирует поступающие ответы (ICMP Echo-Reply)
        Ну или тупо - пингует свитч
        :return: True or False (True - если свитч отправляет ICMP Echo-Reply или пингуется)
        """
        current_function = 'Switch.Ping'

        ping_process = Popen(['ping', '-c', '2', self.host], stdout=PIPE)
        ping_process.communicate()

        if not ping_process.returncode:
            return True
        # Если сетевое оборудование - недоступно (к нам не пришли ICMP ответы), то пробуем послать еще
        # 20 ICMP запросов и если оборудование нам ответит, то вернем True иначе False
        ping_process = Popen(['ping', '-c', '60', self.host], stdout=PIPE)
        ping_process.communicate()
        if not ping_process.returncode:
            return True
        self.log.error('{}: Хост {} - недоступен!'.format(current_function, self.host))
        return False

    def connect(self):
        """
        Метод подключается к свитчу и возвращает сессию
        :return: открытая telnet сессия
        """
        current_function = 'Switch.Connect'

        login = self.config['login']
        password = self.config['password']
        port = 23  # Стандартный telnet порт

        if not self.ping():
            self.log.error('{}: Соединение сброшено - Невозможно подключиться к {}'.format(current_function, self.host))
            return False
        session = telnetlib.Telnet(self.host, port)
        session.write(login.encode('utf-8') + b"\n")
        session.write(password.encode('utf-8') + b"\n")
        sleep(5)
        # Дважды пробуем зайти на свитч из-за возможно включенного TACACS+ (на свитчах, на которых уже залит конфиг)
        session.write(login.encode('utf-8') + b"\n")
        session.write(password.encode('utf-8') + b"\n")
        sleep(2)
        return session

    def get_firmware_version(self):
        """
        Получает текущую версию прошивки
        :return: версия прошивки or False (если невозможно определить версию)
        """
        current_function = 'Switch.get_firmware_version'

        session = self.connect()
        if not session:
            self.log.error('{}: Невозможно получить версию прошивки у свитча {}'.format(current_function, self.host))
            return False

        session.write(self.SHOW_INFO.encode('utf-8') + b'\n')
        sleep(3)
        field = session.read_until(b'System Name: ', 2)
        session.write(b'logout' + b"\n")
        session.close()
        lines = field.decode('utf-8').split('\n')
        if not lines:
            self.log.error('{}: Невозможно получить версию прошивки у свитча {}'.format(current_function, self.host))
            return False

        firmware_version = ''

        for i in range(len(lines)):
            if 'Firmware Version' in lines[i]:
                firmware_version = lines[i][lines[i].find(':') + 2:]
                break

        if not firmware_version:
            self.log.error('{}: Невозможно получить версию прошивки у свитча {}'.format(current_function, self.host))
            return False
        return firmware_version

    def get_info(self):
        """
        Получает информацию со свитча (имя модели, мак адрес, серийный номер)
        :return: Кортеж из текстовых переменных: model_name, mac_address, serial_number
        """
        current_function = 'Switch.get_info'

        session = self.connect()
        if not session:
            self.log.error('{}: Невозможно получить информацию со свитча - {}'.format(current_function, self.host))
            return False

        session.write(self.SHOW_INFO.encode('utf-8') + b'\n')
        sleep(1)
        field = session.read_until(b'System Name: ', 2)
        session.write(b'logout' + b"\n")
        session.close()
        lines = field.decode('utf-8').split('\n')
        if not lines:
            self.log.error('{}: Невозможно получить информацию со свитча - {}'.format(current_function, self.host))
            return False

        # model_name = ''
        # пока решил отключить ф-ию проверки имени модели
        # (т.к. имя модели в базе, отличается от имени модели на свитче)
        mac_address = ''
        serial_number = ''

        for line in lines:
            # if 'Device Type' in line:
            #     model_name = line[line.find(':') + 2:]
            #     # Некоторые модели свитчей имеют Device Type - "DES-3200-28 Fast Ethernet Switch"
            #     # которое необходимо привести к виду - "DES-3200-28" удалив строку после пробела
            #     space = model_name.find(' ')
            #     if space:
            #         model_name = model_name[:space]
            # В старых моделях DES-3526 отсутствует серийный номер!!!!
            if 'MAC Address' in line:
                mac_address = line[line.find(':') + 2:]
            elif 'Serial Number' in line:
                serial_number = line[line.find(':') + 2:]

        if not (mac_address and serial_number):
            self.log.error('{}: Невозможно получить серийний номер '
                           'или мак адрес со свитча - {}'.format(current_function, self.host))
            return False
        return mac_address.rstrip(), serial_number.rstrip()

    def _send_command(self, command):
        """
        Отправляет комманду свитчу по телнет
        :param command: Команда отправляемая свитчу по telnet
        :return: True or False (True - если команда прошла успешно)
        """
        current_function = 'Switch.Send_command'

        session = self.connect()
        if not session:
            self.log.error('{}: Невозможно выполнить команду у свитча {}'.format(current_function, self.host))
            return False
        session.write(command.encode('utf-8') + b"\n")
        sleep(5)
        session.write(b'logout' + b"\n")
        session.close()
        return True

    def enable_dhcp_client(self):
        """
        Активация dhcp client на оборудовании
        :return:
        """
        success = self._send_command(self.ENABLE_DHCP_CLIENT)
        sleep(10)  # Режим ожидания получения нового IP адреса
        if not success:
            return False
        return True

    def reboot(self):
        """
        Перезагрузка оборудования
        :return:
        """
        success = self._send_command(self.DEVICE_REBOOT)
        if not success:
            return False
        return True

    def enable_autoimage(self):
        """
        Включение автопрошивки
        :return:
        """
        success = self._send_command(self.ENABLE_AUTOIMAGE)
        if not success:
            return False
        return True

    def disable_autoimage(self):
        """
        Отключение автопрошивки
        :return:
        """
        success = self._send_command(self.DISABLE_AUTOIMAGE)
        if not success:
            return False
        return True

    def enable_autoconfig(self):
        """
        Включение автоконфигурации
        :return:
        """
        success = self._send_command(self.ENABLE_AUTOCONFIG)
        if not success:
            return False
        return True

    def disable_autoconfig(self):
        """
        Отключение автоконфигурации
        :return:
        """
        success = self._send_command(self.DISABLE_AUTOCONFIG)
        if not success:
            return False
        return True

    def saving_settings(self):
        """
        Сохранение настроек
        :return:
        """
        success = self._send_command(self.SAVING_SETTINGS)
        if not success:
            return False
        return True

    def fix_config(self):
        """
        Исправляет (при необходимости) конфигурацию
        (оборудование доступно, выключена автопрошивка, выключена автоконфигурация, включен dhcp client)
        :return:
        """
        current_function = 'Switch.Fix_config'
        self.log.info('{}Узнаем доступен ли хост - {}'.format(current_function, self.host))
        if not self.ping():
            self.log.error('{}: Невозможно исправить конфиг, т.к. хост {} недоступен!'.format(current_function,
                                                                                              self.host))
            return False

        com_disable_autoconfig = b'disable autoconfig'
        com_disable_autoimage = b'disable autoimage'
        com_enable_dhcp_client = b'config ipif System dhcp'
        com_save = b'save'

        session = self.connect()
        if not session:
            self.log.error('{}: Невозможно исправить конфиг, '
                           'т.к. хост {} недоступен!'.format(current_function, self.host))
            return False

        self.log.info('{}: Выключаем autoconfig на хосте {}'.format(current_function, self.host))
        session.write(com_disable_autoconfig + b'\n')
        sleep(3)
        self.log.info('{}: Выключаем autoimage на хосте {}'.format(current_function, self.host))
        session.write(com_disable_autoimage + b'\n')
        sleep(3)
        self.log.info('{}: Включаем dhcp client на хосте {}'.format(current_function, self.host))
        session.write(com_enable_dhcp_client + b'\n')
        sleep(3)
        self.log.info('{}: Сохраняем настройки на хосте {}'.format(current_function, self.host))
        session.write(com_save + b'\n')
        sleep(5)
        return True

    def config_compliance_check(self):
        """
        Проверка свитча на наличие матричного конфига
        :return: True or False (True - если на свитче новый конфиг)
        """
        current_function = 'Switch.config_compliance_check'

        session = self.connect()
        if not session:
            self.log.error('{}: Невозможно проверить свитч {} '
                           'на наличие матричного конфига'.format(current_function, self.host))
            return False

        session.write(self.SHOW_INFO.encode('utf-8') + b'\n')
        sleep(3)
        field = session.read_until(b'System Name ', 2)
        session.write(b'logout' + b"\n")
        session.close()
        lines = field.decode('utf-8').split('\n')

        # необходимо проверить управляющий влан:
        # если - manager, то конфиг залился,
        # если - default, то нет!

        for line in lines:
            if 'VLAN Name' in line:
                separator = line.find(':')
                vlan_name = line[separator + 2:]
                if 'manager' in vlan_name:  # in - т.к. есть пробел в конце vlan_name
                    return True
                return False

    def port_enable(self, port):
        """
        Включает порт у свитча используя протокол SNMP
        :param port: Порт коммутатора, который необходимо включить
        :return: False  - если хост недоступен и невозможно включить порт
        """

        current_function = 'Switch.Port_enable'

        try:
            # Значения: 1 - up, 2 - down, 3 - testing
            snmp_set('IF-MIB::ifAdminStatus.{}'.format(str(port)), 1, hostname=self.host, community='orion_comm',
                     version=2)
            # долгая проверка линка порта, без нее моментально влючает порт!
            # if not self.get_port_status(port):
            #     # Если линк на порту не поднялся, ждем 5 секунд и еще раз проверяем
            #     sleep(5)
            # if not self.get_port_status(port):
            #     return False
            return True
        except exceptions.EasySNMPTimeoutError:
            self.log.error('{}: Хост {} - недоступен'.format(current_function, self.host))
            return False

    def port_disable(self, port):
        """
        Отключает порт у свитча используя протокол SNMP
        :param port: Порт коммутатора, который необходимо отключить
        :return: False  - если хост недоступен и невозможно отключить порт
        """
        current_function = 'Switch.Port_disable'

        try:
            # Значения: 1 - up, 2 - down, 3 - testing
            snmp_set('IF-MIB::ifAdminStatus.{}'.format(str(port)), 2, hostname=self.host, community='orion_comm',
                     version=2)
            return True
        except exceptions.EasySNMPTimeoutError:
            self.log.error('{}: Хост {} - недоступен'.format(current_function, self.host))
            return False

    def get_mac_on_port(self, port):
        """
        Возвращает mac адрес с указанного порта
        :param port: Порт коммутатора, с которого необходимо получить мак адрес
        :return: MAC адрес or False (в случае если невозможно получить мак адрес с данного порта)
        """
        current_function = 'Switch.Get_mac_on_port'

        mac_list = []
        counter = 5  # Счетчик попыток взять мак адрес с порта

        while counter:
            counter -= 1
            try:
                mac_addresses = snmp_walk(
                    '1.3.6.1.2.1.17.7.1.2.2.1.2', hostname=self.host, community='orion_comm', version=2)
            except exceptions.EasySNMPTimeoutError:
                self.log.error('Хост {} - недоступен'.format(self.host))
                return False

            for octet in mac_addresses:
                # Ага согласно этому snmp oid'у значения у него это порт а сам оид состоит из мака
                # в десятичной системе счисления
                switch_port = octet.value
                if switch_port != str(port):
                    continue
                # TODO протестить метод со свитчем без мака!!!
                # преобразуем строку oid'а вида iso.3.6.1.2.1.17.7.1.2.2.1.2.1998.40.59.130.1.246.64
                # в список из 6 октетов в hex формат
                oid_line = octet.oid.split('.')[-6:]  # последние 6 значений списка это мак адрес
                for bit in oid_line:
                    hex_mac = hex(int(bit))
                    hex_mac = hex_mac[2:]  # удаляем лишнии символы
                    if len(hex_mac) == 1:
                        hex_mac = '0' + hex_mac
                    mac_list.append(hex_mac.upper())

            if len(mac_list) != 6:
                # бывает что свитч ен показывает мак с порта. т.к. с порта не идет никакой траффик и таблица
                # мак адресов очищается. Чтобы посмотреть мак с порта, необходимо порт выключить и включить заново
                self.port_disable(port)
                sleep(1)
                self.port_enable(port)
                sleep(10)
                continue

            if len(mac_list) == 6:
                mac = "{}-{}-{}-{}-{}-{}".format(*mac_list)
                return mac

            self.log.error('{}: Нет мак адреса у хоста {} с порта {}'.format(current_function, self.host, port))
            return False

    def get_port_status(self, port):
        """
        Показывает статус указанного порта (включен или выключен)
        :param port:
        :return: MAC адрес or False (в случае если невозможно получить мак адрес с данного порта)
        """
        current_function = 'Switch.get_port_status'

        try:
            port_status = snmp_get('IF-MIB::ifOperStatus.{}'.format(str(port)), hostname=self.host,
                                   community='orion_comm', version=2)
        except exceptions.EasySNMPTimeoutError:
            self.log.error('Хост {} - недоступен'.format(self.host))
            return False
        else:
            if port_status.value == 'NOSUCHINSTANCE':
                self.log.error('{}: Отсутствует {} порт у свитча {}'.format(current_function, port, self.host))
                return False
            status = port_status.value
            if status == '1':
                return True
            return False

    def get_active_ports(self):
        """
        Получает список всех активных портов коммутатора
        :return: Список активных портов
        """
        # Включаем все порты:
        for port in range(1, 23):
            self.port_enable(port)
        sleep(5)

        try:
            port_status = snmp_walk('IF-MIB::ifOperStatus', hostname=self.host, community='orion_comm', version=2)
        except exceptions.EasySNMPTimeoutError:
            self.log.error('Хост {} - недоступен'.format(self.host))
            return False
        else:
            active_ports = []

            for port, line in enumerate(port_status):
                status = line.value
                switch_port = port + 1
                # 24 порт у регистратора может быть приходом (транковым)
                if int(switch_port) < 24 and int(status) == 1:
                    active_ports.append(switch_port)

            # Отключаем все порты:
            for port in range(1, 23):
                self.port_disable(port)
            sleep(5)

            if not active_ports:
                return False
            return active_ports
