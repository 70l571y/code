/*
1) Считывает все ключи БД Redis, в которых есть мак адрес (Ключи представленны в виде мак адресов, значения в виде
ip-адресов)
2) Ищет свитч по i-тому ключу (мак адресу) в Красноярском продакшине
    2.1) Если свитча нет в продакшине, то переходит к следующему мак адресу
    2.2) Если свитч в продакшине, то ищет мак адрес свитча в конфиге DHCP
        2.2.1) Если есть запись с данным мак адресом в конфиге DHCP, то сверяет все сетевые настройки свитча с
        БД SWDB (switchbase)
            2.2.1.1) Если сетевые настройки свитча совпадают с БД SWDB, то переходит в п.2)
            2.2.1.2) Если сетевые настройки свитча не совпадают с БД SWDB, то запись удаляется и добавляется новая с
            корректными сетевыми настройками
        2.2.2) Если нет записи с данным мак адресом в конфиге DHCP, то добавляет запись в конфиг с нужными настройками
3) После того как считал и обработал последний ключ с БД Redis, смотрит были ли изменения в конфиге DHCP
    3.1) Если изменения были в конфиге, то перезагружает DHCP сервер и переходит в п.1)
    3.2) Если изменений не было, переходит в п.1)
 */

package main

import (
	"log"
	"os"
	"os/exec"
	"regexp"
	"time"

	m "GoglandProjects/dhcp_conf_collector/modules"
)

var (
	//client     *redis.Client
	rebootDHCP = false // Индикатор для ф-ии перезагрузки DHCP сервера (true - для перезагрузки)
)

func main() {
	logFile, _ := os.OpenFile(m.LogFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
	defer logFile.Close()
	log.SetOutput(logFile)
	macAddrRex := regexp.MustCompile("((?:[0-9A-F]{2}-){5}[0-9A-F]{2})")
	for {
		// Каждый раз проверяем коннект к БД Редис
		m.ConnectToRedis()

		if rebootDHCP {
			// Перезагружаем DHCP сервер
			log.Println("Перезагрузка DHCP сервера!")
			if err := exec.Command("service", "isc-dhcp-server", "restart").Run(); err != nil {
				m.Check(err)
				log.Println("Невозможно перезагрузить DHCP сервер")
			}
			rebootDHCP = false
			time.Sleep(time.Second * 5) //время ожидания перезагрузки DHCP сервера
		}

		// Собираем все ключи Redis
		redisAllKeys, err := m.Client.Keys("*").Result()
		m.Check(err)
		redisMacAddresses := make([]string, 0, len(redisAllKeys))
		for _, key := range redisAllKeys {
			mac := macAddrRex.FindAllString(key, -1)
			// Если в Redis попадется ключ не с мак адресом, то берем следующий
			if len(mac) == 0 {
				continue
			}
			// Собираме слайс только из мак адресов
			redisMacAddresses = append(redisMacAddresses, mac[0])
		}
		// Очищаем конфиг DHCP сервера от лишних устройств, которых нет в Redis
		m.Clean(&redisMacAddresses)
		// Получаем ссылку на слайс из мак адресов, которые находятся в продакшине
		productionSwitches := m.GetProductionSwitches(&redisMacAddresses)
		for _, mac := range *productionSwitches {
			// Ищем мак адрес в файле конфига DHCP сервера
			if m.SearchMac(&mac) {
				// Сравниваем сетевые настройки хоста в файле конфига с настройками из БД SWDB
				if m.CheckNetworkSettings(&mac) {
					// Если совпадают - значит все ОК и идем дальше
					continue
				} else {
					// Если не совпадают, то удаляем запись из конфига DHCP сервера и добавляем с нужными настройками
					log.Printf("Не совпадают настройки с БД свитча - %s", mac)
					log.Println("Удаляем запись из конфига DHCP сервера и добавляем с нужными настройками")
					m.RemoveEntry(&mac)
					m.AddEntry(&mac)
					rebootDHCP = true
					continue
				}
			} else {
				// Если нет такого мак адреса в конфиге, то его добавляем и перезагружаем DHCP сервер
				log.Printf("Нет мак адреса - %s в конфиге DHCP!. Добваляем.", mac)
				m.AddEntry(&mac)
				rebootDHCP = true
				continue
			}
		}
		// Время отдыха между циклами полного чтения Редис
		m.Client.Close()
		time.Sleep(time.Second * time.Duration(m.UpdateInterval))
	}
}
