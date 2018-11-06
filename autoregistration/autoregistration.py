#!/usr/bin/env python3

# Скрипт автоматизирует прошивку и предварительную конфигурацию коммутаторов
#  v.0.1 [20.04.2018]
# Автор: Сидоркин Роман Леонидович, sidorkin.r@orionnet.ru,+7905-974-3304

import sys
from time import sleep
from threading import Thread

from modules.db import DB
from modules.log import Log
from modules.dhcp import DHCP
from modules.config import Config
from modules.switch import Switch
from modules.broker import RabbitMessageChecker


class Autoregistration:
    log = Log()
    database = DB()
    dhcp = DHCP()

    HOST_IP_ADDRESS = '10.90.90.90'  # ip адрес по умолчанию для коммутаторов D-Link

    SWITCH_ERRORS = 0  # Ошибки во время автоконфигурации

    def __init__(self):
        # Полчить ip адрес регистратора из конфига
        if 'registrar' not in Config.read():
            self.log.critical('Отсутствует IP адрес регистратора в файле конфига!')
            self.REGISTRAR_IP_ADDRESS = None
        self.REGISTRAR_IP_ADDRESS = Config.read()['registrar']['ip']

        # Создаем объект регистратор (свитч к которому подключено настраиваемое оборудование)
        self.registrar = Switch(host=self.REGISTRAR_IP_ADDRESS)

    def switch_compliance_check(self, host, mac_address, list_switches):
        """
        Проверка соответствия модели оборудования той, для которой был запущен поток настройки
        :param: ip адрес свитча
        :param: Список свитчей в табшице autoconfig
        :return: True or False (True если проверка прошла успешно)
        """
        current_function = 'Switch compliance check'

        switch = Switch(host=host)

        switch_info = switch.get_info()
        # из списка мы узнаем id свитчей, а по ним и мак адресу нужных
        # коннектимся к свитчу по телнету и возвращаем кортеж из: mac_address, serial_number
        if not switch_info:
            self.log.error('{}: Невозможно получить '
                           'серийный номер и мак адрес со свитча - {}'.format(current_function, host))
            return False

        switch_mac_address = switch_info[0].upper()
        if not switch_mac_address:
            self.log.error('{}: Невозможно получить мак адрес со свитча - {}'.format(current_function, host))
            return False

        serial_number = switch_info[1].upper()
        if not serial_number:
            self.log.error('{}: Невозможно получить серийный номер со свитча - {}'.format(current_function, host))
            return False

        # Берем инфу из пула по списку автонастройки
        serial_number_from_db = self.database.get_switch_info(mac_address, list_switches)
        serial_number_from_db = serial_number_from_db.upper()  # в базе серйиники могут быть в lowecase!
        if not serial_number_from_db:
            self.log.error('{}: Нет такого свитча в '
                           'списке автонастройки - {}!'.format(current_function, mac_address))
            return False
        if (serial_number == serial_number_from_db) and (switch_mac_address == mac_address):
            return True
        return False

    def hardware_configuration(self, mac_address, autoconfig_id, list_switches, current_switch_id, port):
        """
        Метод (поток) настройки оборудования прошивает свитчи и загружает на них матричный конфиг
        :param mac_address: Мак адрес текущего свитча
        :param autoconfig_id: ID записи в таблице autoconfig базы switchbase со списком свитчей для автонастройки
        :param list_switches: Список свитчей для автонастройки
        :param current_switch_id: ID текущего свитча в списке автонастройки
        :param port: Порт регистратора, от которого работает настраиваемый свитч
        """
        self.log.info('[CONFIG][Port: {}] Работает поток настройки оборудования'.format(port))

        # Запрашиваем новый ip адрес еще раз (а то мало ли)
        current_ip = self.dhcp.get_ip(mac_address)
        if not current_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Невозможно получить новый IP адрес свитча'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Невозможно получить новый IP адрес свитча')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        host_dhcp_ip = Switch(host=current_ip)

        # Обновляем статус записи настраиваемого оборудования в таблице autoconfig базы switchbase
        self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, port=port,
                                             status='working')

        # Получаем текущую версию прошивки свитча до включения автопрошивки
        self.log.info('[CONFIG][{}][Port: {}] '
                      'Получаем текущую версию прошивки свитча до включения автопрошивки'.format(current_ip, port))
        default_firm_version = host_dhcp_ip.get_firmware_version()
        if not default_firm_version:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Невозможно получить версию прошивки'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Невозможно получить версию прошивки')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока
        self.log.info('[CONFIG][{}][Port: {}] '
                      'Текущая версия прошивки - {}'.format(current_ip, port, default_firm_version))

        # Включаем автопрошивку
        self.log.info('[CONFIG][{}][Port: {}] Активация ф-ии автопрошивки'.format(current_ip, port))
        enable_autoimage_host_dhcp_ip = host_dhcp_ip.enable_autoimage()
        if not enable_autoimage_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] Не удалось включить автопрошивку'.format(
                self.HOST_IP_ADDRESS, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось включить автопрошивку')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Сохраняем настройки
        self.log.info('[CONFIG][{}][Port: {}] Сохранение настроек'.format(current_ip, port))
        saving_settings_host_dhcp_ip = host_dhcp_ip.saving_settings()
        if not saving_settings_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось сохранить настройки'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось сохранить настройки')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Перезагружаем оборудование
        self.log.info('[CONFIG][{}][Port: {}] Перезагрузка оборудования'.format(current_ip, port))
        device_reboot_host_dhcp_ip = host_dhcp_ip.reboot()
        if not device_reboot_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось перезагрузить свитч'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось перезагрузить свитч')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Ждем пока загрузится
        self.log.info('[CONFIG][{}][Port: {}] Ожидание 800 секунд для прошивки свитча'.format(current_ip, port))
        sleep(800)  # Время загрузки оборудования (1.5 min) + время прошивки (12 min)

        # Отключаем автопрошивку
        self.log.info('[CONFIG][{}][Port: {}] Отключение автопрошивки'.format(current_ip, port))
        disable_autoimage_host_dhcp_ip = host_dhcp_ip.disable_autoimage()
        if not disable_autoimage_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось отключить автопрошивку'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось отключить автопрошивку')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Включаем автоконфиг
        self.log.info('[CONFIG][{}][Port: {}] Включение автоконфигурации'.format(current_ip, port))
        enable_autoconfig_host_dhcp_ip = host_dhcp_ip.enable_autoconfig()
        if not enable_autoconfig_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось включить автоконфиг'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось включить автоконфиг')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Сохраняем настройки
        self.log.info('[CONFIG][{}][Port: {}] Сохранение настроек'.format(current_ip, port))
        saving_settings_host_dhcp_ip = host_dhcp_ip.saving_settings()
        if not saving_settings_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось сохранить настройки'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось сохранить настройки')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Перезагружаем оборудование
        self.log.info('[CONFIG][{}][Port: {}] Перезагрузка оборудования'.format(current_ip, port))
        device_reboot_host_dhcp_ip = host_dhcp_ip.reboot()
        if not device_reboot_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось перезагрузить свитч'.format(current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось перезагрузить свитч')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        self.log.info('[CONFIG][{}][Port: {}] Ожидание 180 секунд для перезагрузки свитча'.format(current_ip, port))
        sleep(180)  # Время загрузки оборудования

        # Получаем новый ip адрес (с новым конфигом придет новый ip)
        self.log.info('[CONFIG][Port: {}] Запрос на получение нового ip адреса')
        new_current_ip = self.dhcp.get_ip(mac_address)
        if not new_current_ip:
            self.log.info('[CONFIG][Port: {}] '
                          'Невозможно получить новый IP адрес свитча'.format(port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Невозможно получить новый IP адрес свитча')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока
        self.log.info('[CONFIG][Port: {}] Текущий ip адрес свитча - {}'.format(port, new_current_ip))

        host_new_dhcp_ip = Switch(host=new_current_ip)

        # Отключаем автоконфиг
        self.log.info('[CONFIG][{}][Port: {}] Отключение автоконфигурации'.format(new_current_ip, port))
        disable_autoconfig_host_new_dhcp_ip = host_new_dhcp_ip.disable_autoconfig()
        if not disable_autoconfig_host_new_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось отключить автоконфиг'.format(new_current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось отключить автоконфиг')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Сохраняем настройки
        self.log.info('[CONFIG][{}][Port: {}] Сохранение настроек'.format(new_current_ip, port))
        saving_settings_host_dhcp_ip = host_new_dhcp_ip.saving_settings()
        if not saving_settings_host_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось сохранить настройки'.format(new_current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось сохранить настройки')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Проверяем исправляем настройки свитча
        self.log.info('[CONFIG][{}][Port: {}] Проверка и исправление конфигурации'.format(new_current_ip, port))
        fix_config_host_new_dhcp_ip = host_new_dhcp_ip.fix_config()
        if not fix_config_host_new_dhcp_ip:
            self.log.info('[CONFIG][{}][Port: {}] '
                          'Не удалось проверить и исправить конфигурацию'.format(new_current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не удалось проверить и исправить конфигурацию')
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Проверяем загрузился ли свитч с новой прошивкой
        ping_host_new_dhcp_ip = host_new_dhcp_ip.ping()
        if not ping_host_new_dhcp_ip:
            self.log.error('[CONFIG][{}][Port: {}] '
                           'Свитч с новой прошивкой - не загрузился'.format(new_current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Не загрузился с новой прошивкой')
            self.registrar.port_disable(port)
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока

        # Проверяем - обновилась ли прошивка на оборудовании
        self.log.info('[CONFIG][{}][Port: {}] Проверка текущей версии прошвики'.format(new_current_ip, port))
        # Получаем текущую версию прошивки (после перепрошивки)
        current_firmware_version = host_new_dhcp_ip.get_firmware_version()
        # Если версия прошивки до прошивки свитча равна версии после прошивки свитча, то свитч не прошился!
        if current_firmware_version == default_firm_version:
            self.log.error('[CONFIG][{}][Port: {}] Прошивка не обновилась'.format(new_current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Прошивка не обновилась')
            self.registrar.port_disable(port)
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока
        self.log.info('[CONFIG][{}][Port: {}] Новая прошивка загрузилась'.format(new_current_ip, port))

        # Проверяем - залился ли матричный конфиг на оборудование
        self.log.info('[CONFIG][{}][Port: {}] '
                      'Проверка наличия матричного конфига на свитче'.format(new_current_ip, port))
        config_compliance_check = host_new_dhcp_ip.config_compliance_check()
        if not config_compliance_check:
            self.log.error('[CONFIG][{}][Port: {}] Матричный конфиг не загружен'.format(new_current_ip, port))
            self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                 errors='Конфиг не залился')
            self.registrar.port_disable(port)
            self.SWITCH_ERRORS = 1
            sys.exit(1)  # выходим только из данного потока
        self.log.info('[CONFIG][{}][Port: {}] Матричный конфиг на свитче успешно загружен'.format(new_current_ip, port))
        self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='done')
        self.registrar.port_disable(port)

    def equipment_preparation(self, autoconfig_id, list_switches):
        """
        Метод (поток) поток предварительной подготовки оборудования смотрит на регистраторе подключенные свитчи,
        сверяет их со списком свитчей, которые нужно настроить, активирует dhcp клиента на свитчах и передает
        настройку свитчей методу (потоку) настройки оборудования
        :param autoconfig_id: ID записи в таблице autoconfig базы switchbase со списком свитчей для автонастройки
        :param list_switches: Список свитчей для автонастройки
        """
        # TODO Добавить выбор IP регистратора в зависимости от города, куда настроено оборудование
        hardware_configuration_thread = None
        host_default_ip = Switch(host=self.HOST_IP_ADDRESS)

        self.log.info('[PREPARATION] Работает поток предварительной подготовки оборудования')
        self.log.info('[PREPARATION] Ждем 180 секунд для загрузки всех свитчей')

        sleep(180)  # режим ожидания загрузки оборудования, время ожидания 3 минуты
        # Получаем список портов, на которых есть линки (и работаем только с данными портами)
        active_ports = self.registrar.get_active_ports()

        if not active_ports:
            self.log.error('[PREPARATION][{}] Нет линка на всех портах!!!'.format(self.REGISTRAR_IP_ADDRESS))
            self.SWITCH_ERRORS = 1
            self.log.info('[PREPARATION] Выход из потока предварительной подготовки оборудования')
            sys.exit(1)  # выходим только из данного потока
        self.log.info('[PREPARATION][{}] На портах {} есть линки'.format(self.REGISTRAR_IP_ADDRESS, active_ports))

        # По одному включаем порты регистратора
        for port in active_ports:
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Включение {} порта'.format(self.REGISTRAR_IP_ADDRESS, port, port))
            self.registrar.port_enable(port)  # Включаем порт на регистраторе
            sleep(5)  # Подождем пока поднимится порт
            port_enable_registrar = self.registrar.get_port_status(port)
            if not port_enable_registrar:
                self.log.info('[PREPARATION][{}][Port: {}] '
                              'Нет линка на {} порту'.format(self.REGISTRAR_IP_ADDRESS, port, port))
                self.SWITCH_ERRORS = 1
                continue

            # Получаем мак адрес с порта
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Полчаем мак адрес свитча'.format(self.REGISTRAR_IP_ADDRESS, port))
            mac_address = self.registrar.get_mac_on_port(port)
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Мак адрес свитча {}'.format(self.REGISTRAR_IP_ADDRESS, port, mac_address))
            if not mac_address:
                self.log.info('[PREPARATION][{}][Port: {}] '
                              'Нет мак адреса на {} порту'.format(self.REGISTRAR_IP_ADDRESS, port, port))
                self.SWITCH_ERRORS = 1
                continue

            # Полчаем ID свитча из БД SWDB
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Полчаем ID свитча из БД SWDB'.format(self.REGISTRAR_IP_ADDRESS, port))
            current_switch_id = self.database.get_switch_id(mac_address)
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Полчаем ID свитча из БД SWDB {}'.format(self.REGISTRAR_IP_ADDRESS, port, current_switch_id))
            if not current_switch_id:
                self.log.info('[PREPARATION][{}][Port: {}] '
                              'Невозможно получить ID свитча по мак адресу {}'.format(self.REGISTRAR_IP_ADDRESS, port,
                                                                                      mac_address))
                self.SWITCH_ERRORS = 1
                continue

            # Проверяем доступно ли оборудование с заводским ip адресом - 10.90.90.90
            self.log.info('[PREPARATION][{}][Port: {}] Проверка доступен ли свитч'.format(self.HOST_IP_ADDRESS, port))
            ping_switch = host_default_ip.ping()
            if not ping_switch:
                # если свитч не пингуется можно попробовать отключить и включить порт (иногда помогает)
                self.registrar.port_disable(port)
                sleep(1)
                self.registrar.port_enable(port)
                sleep(10)
            ping_switch = host_default_ip.ping()
            if not ping_switch:
                self.log.info('[PREPARATION][{}][Port: {}] Свитч недоступен'.format(self.HOST_IP_ADDRESS, port))
                self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                     errors='Устройство с IP адресом ({}) - '
                                                            'недоступно'.format(self.HOST_IP_ADDRESS))
                self.registrar.port_disable(port)
                self.SWITCH_ERRORS = 1
                continue
            self.log.info('[PREPARATION][{}][Port: {}] Свитч доступен'.format(self.HOST_IP_ADDRESS, port))

            # Проверяем текущий хост, есть ли он в списке настраиваемых
            self.log.info('[PREPARATION][{}][Port: {}] Проверка текущего свитча, '
                          'есть ли он в списке настраиваемых'.format(self.HOST_IP_ADDRESS, port))
            authorized_switch = self.switch_compliance_check(self.HOST_IP_ADDRESS, mac_address, list_switches)
            if not authorized_switch:
                self.log.info('[PREPARATION][{}][Port: {}] '
                              'Не соответствейт уст-ву из списка автонастройки'.format(self.HOST_IP_ADDRESS, port))
                self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                     errors='Не соответствейт уст-ву из списка автонастройки')
                self.registrar.port_disable(port)
                self.SWITCH_ERRORS = 1
                continue
            self.log.info('[PREPARATION][{}][Port: {}] Свитч есть в списке!'.format(self.HOST_IP_ADDRESS, port))

            # Активируем функцию dhcp client на свитче
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Активация dhcp клиента на свитче'.format(self.HOST_IP_ADDRESS, port))
            enable_dhcp_on_switch = host_default_ip.enable_dhcp_client()
            if not enable_dhcp_on_switch:
                self.log.info('[PREPARATION][{}][Port: {}] '
                              'Невозможно активировать dhcp client на свитче'.format(self.HOST_IP_ADDRESS, port))
                self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                     errors='Невозможно активировать dhcp client')
                self.registrar.port_disable(port)
                self.SWITCH_ERRORS = 1
                continue

            # Получаем новый ip адрес по DHCP
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Получение нового ip адреса по DHCP'.format(self.HOST_IP_ADDRESS, port))
            current_ip = self.dhcp.get_ip(mac_address)
            if not current_ip:
                self.log.info('[PREPARATION][{}][Port: {}] '
                              'Невозможно получить новый IP адрес свитча'.format(self.HOST_IP_ADDRESS, port))
                self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                     errors='Невозможно получить новый IP адрес свитча')
                self.registrar.port_disable(port)
                self.SWITCH_ERRORS = 1
                continue
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Новый ip адрес - {}'.format(self.HOST_IP_ADDRESS, port, current_ip))

            # Проверяем доступен ли свитч с новый IP адресом, полученным по DHCP
            self.log.info('[PREPARATION][{}][Port: {}] '
                          'Проверка доступен ли свитч с ip адресом {}'.format(self.HOST_IP_ADDRESS, port, current_ip))
            host_dhcp_ip = Switch(host=current_ip)
            ping_switch_new_ip = host_dhcp_ip.ping()
            if not ping_switch_new_ip:
                self.log.error('[PREPARATION][{}][Port: {}] Свитч недоступен'.format(current_ip, port))
                self.database.update_autoconfig_info(autoconfig_id, list_switches, current_switch_id, status='error',
                                                     errors='Устройство с новым IP адресом ({}) '
                                                            '- недоступно'.format(current_ip))
                self.registrar.port_disable(port)
                self.SWITCH_ERRORS = 1
                continue
            self.log.info('[PREPARATION][{}][Port: {}] Свитч доступен'.format(current_ip, port))

            # Передаем управление потоку настройки оборудования!!!
            # Демонизируем поток, если вдруг приложение умрет -
            # поток настройки мог корректно завершить процесс настройки свитча
            hardware_configuration_thread = Thread(target=self.hardware_configuration,
                                                   args=(mac_address, autoconfig_id, list_switches, current_switch_id,
                                                         port),
                                                   daemon=True)
            hardware_configuration_thread.start()

        # ждем пока поток предварительной подготовки оборудования закончит свою работу
        while hardware_configuration_thread.is_alive():
            sleep(1)
        self.log.info('[PREPARATION] Выход из потока предварительной подготовки оборудования')

    def run(self):
        self.log.info('[MAIN] Запуск агента')
        # проверяем незавершенную процедуру настройки
        # если такая есть, то завершает данную процедуру
        self.database.checking_the_last_run()

        while True:
            rabbit = RabbitMessageChecker()
            rabbit.run()

            # delivery_tag - Если равен 1, то кролик получил сообщение!
            if not rabbit.delivery_tag:
                # Если нет сообщений от кролика (rabbit.delivery_tag == 0), то ждем 1 секунду и перепроверяем
                sleep(1)
                continue

            message = rabbit.message

            # получаем и обрабатываем типы сообщений от кролика
            message_type = message['type']

            # для запуска процесса автонастройки нам нужен - autoconfig_start
            if 'autoconfig_start' in message_type:
                self.log.info('[MAIN] Пришло сообдение от кролика:{}'.format(message))

                # Получаем id для списка настраиваемых свитчей из таблицы autoconfig от кролика
                autoconfig_id = message['data']['id']
                if not autoconfig_id:
                    self.log.error('[MAIN] Невозможно получить autoconfig_id в сообщении от кролика!')
                    continue

                # Устанавливаем глобальный статус автоконфига на working
                self.database.update_autoconfig_status(autoconfig_id, 'working')

                # Получаем список свитчей для автоконфига по указанному id
                list_switches = self.database.get_autoconf_switches_list(autoconfig_id)
                if not list_switches:
                    self.log.error('[MAIN] Невозможно получить список свитчей')
                    self.log.info('[MAIN] Агент ждет новое сообщение от кролика')
                    continue

                # Запускаем поток предварительной подготовки оборудования
                equipment_preparation_thread = Thread(target=self.equipment_preparation,
                                                      args=(autoconfig_id, list_switches,))
                equipment_preparation_thread.start()
                equipment_preparation_thread.join()

                # Отправляет сообщение в интерфейс об удачном/неудачном завершении прошивки всех свитчей
                if self.SWITCH_ERRORS:
                    self.SWITCH_ERRORS = 0
                    self.database.update_autoconfig_status(autoconfig_id, 'error')
                    self.log.info('[MAIN] Настройка свитчей - завершена с ошибками')
                    self.log.info('[MAIN] Агент ждет новое сообщение от кролика')
                    continue
                self.database.update_autoconfig_status(autoconfig_id, 'done')
                self.SWITCH_ERRORS = 0
                self.log.info('[MAIN] Настройка свитчей - закончена')
                self.log.info('[MAIN] Агент ждет новое сообщение от кролика')
            else:
                self.log.error('[MAIN] Агент не знает как обратывать '
                               'такой тип сообщения от кролика - {}'.format(message))
                self.log.info('[MAIN] Агент ждет новое сообщение от кролика')


if __name__ == '__main__':
    process = Autoregistration()
    process.run()
