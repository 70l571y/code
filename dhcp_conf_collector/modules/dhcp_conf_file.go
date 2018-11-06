package modules

import (
	"bufio"
	"bytes"
	"fmt"
	"io/ioutil"
	"os"
	"regexp"
	"strings"
)

func SearchMac(mac *string) bool {
	// Поиск мак адреса в конфиге DHCP сервера
	/* Получаем мак вида: A0-AB-1B-FC-F5-55
	а в конфиге он в формате: a0:ab:1b:fc:f5:55
	*/
	*mac = strings.ToLower(*mac)
	*mac = strings.Replace(*mac, "-", ":", -1)
	file, err := os.Open(DHCPConfFilePath)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	line := 1

	for scanner.Scan() {
		if strings.Contains(scanner.Text(), *mac) {
			return true
		}
		line++
	}
	return false
}

func RecordEntry(mac *string) *string {
	// Формирование записи для конфига DHCP сервера
	configMac := strings.ToLower(*mac)
	configMac = strings.Replace(*mac, "-", ":", -1)
	dbIPAddress, dbSubnet, dbGateway, dbNetmask := GetNetworkSettings(mac)
	hostName := fmt.Sprintf("%s", strings.Replace(*mac, ":", "-", -1))
	entry := fmt.Sprintf("subnet %s netmask %s {\nauthoritative;\noption routers %s;\nhost %s {\nhardware ethernet %s;\nfixed-address %s;\n}\n}\n",
		dbSubnet, dbNetmask, dbGateway, hostName, configMac, dbIPAddress)
	return &entry
}

func CheckNetworkSettings(mac *string) bool {
	var (
		configEntrySlice []string
		configEntry      string
		configMac        string
	)
	/* приводим мак адрес в формат конфига DHCP сервера:
	40-9B-CD-FC-DE-46 - получаем из функции
	40:9b:cd:fc:de:46 - формат конфига DHCP сервера
	*/
	configMac = strings.ToLower(*mac)
	configMac = strings.Replace(*mac, "-", ":", -1)

	// Считываем конфиг DHCP сервера и ищем мак адрес
	input, err := ioutil.ReadFile(DHCPConfFilePath)
	Check(err)
	lines := strings.Split(string(input), "\n")
	for i, line := range lines {
		// Если есть мак в конфиге, то считываем настройки свитча по данному мак адресу
		if strings.Contains(line, configMac) {
			// Запись состоит из 4-х строк до строки с мак адресом и 2-х строк после + еще две скобки "}}" после
			configEntrySlice = lines[i-4: i+4]
		}
	}
	// Собираем строку из слайса
	if configEntrySlice != nil {
		for _, i := range configEntrySlice {
			configEntry += i + "\n"
		}
	}

	dbEntry := RecordEntry(&configMac)

	// Сравниваем запись в конфиге DHCP сервера с записью в БД SWDB
	if configEntry == *dbEntry {
		return true
	} else {
		return false
	}
	return false
}

func RemoveEntry(mac *string) {
	// Удаляем запись из конфига с данным мак адресом
	var (
		configEntrySlice []string
		configEntry      string
		configMac        string
	)
	// Исправляем формат мак адреса
	configMac = strings.ToLower(*mac)
	configMac = strings.Replace(configMac, "-", ":", -1)
	// Ищем данный мак адрес в файле конфига DHCP сервера
	configFile, err := ioutil.ReadFile(DHCPConfFilePath)
	Check(err)
	lines := strings.Split(string(configFile), "\n")
	for i, line := range lines {
		// Если есть мак в конфиге, то считываем настройки свитча по данному мак адресу
		if strings.Contains(line, configMac) {
			configEntrySlice = lines[i-4: i+4]
		}
	}
	// Собираем строку из слайса
	if configEntrySlice != nil {
		for _, i := range configEntrySlice {
			configEntry += i + "\n"
		}
	}

	newLines := bytes.Replace(configFile, []byte(configEntry), []byte(""), 1)
	err = ioutil.WriteFile(DHCPConfFilePath, newLines, 0644)
	Check(err)
}

func AddEntry(mac *string) {
	var findEntry string
	// Добавления записи в конец файла конфига DHCP сервера
	// Исправляем формат мак адреса
	configMac := strings.ToLower(*mac)
	configMac = strings.Replace(configMac, "-", ":", -1)

	// // Получаем сформированную запись для конфига DHCP
	configEntry := RecordEntry(&configMac)

	// Считываем файл конфига
	configFile, err := ioutil.ReadFile(DHCPConfFilePath)
	Check(err)

	lines := strings.Split(string(configFile), "\n")

	findEntrySlice := lines[len(lines)-5:]
	for _, i := range findEntrySlice {
		findEntry += i + "\n"
	}
	findEntry = findEntry[:len(findEntry)-1]
	/*
		В начало записи добавляем две закрывающиеся скобки "}}".
		Т.к. мы заменяем "}}}" в конце файла конфига на "}}" + сформированная запись + "}"
		тем самым мы делаем вставку записи между 2-й и третьей скобкой
	*/
	moveEntry := findEntry[:len(findEntry)-1] + *configEntry + "}"
	/*
		В конце файла конфига вседа стоит запись из 3 закрывающиехся фигурных скобок "}}}".
		Заменяем данную запись на уже сформированную
	*/

	remLine := bytes.Replace(configFile, []byte(findEntry), []byte(moveEntry), 1)
	err = ioutil.WriteFile(DHCPConfFilePath, remLine, 0644)
	Check(err)
}

func Clean(redisMacList *[]string) {
	// Удаляет лишние записи в конфиге DHCP
	// Получает список мак адресов с БД Redis и удаляет те записи в конфиге DHCP,
	// в которых в которых нет этих адресов
	var found = false

	macAddrRex := regexp.MustCompile("((?:[0-9a-f]{2}:){5}[0-9a-f]{2})")
	configFile, err := ioutil.ReadFile(DHCPConfFilePath)
	Check(err)
	configLines := strings.Split(string(configFile), "\n")

	for _, line := range configLines {
		// Получаем мак адрес с файла конфига с помощью регулярного выражения
		searchMac := macAddrRex.FindAllString(line, -1)
		if len(searchMac) == 0 {
			continue
		}
		mac := searchMac[0]
		// Переводим мак адрес конфига в мак адрес Redis, для сравнения
		configMac := strings.ToUpper(mac)
		configMac = strings.Replace(configMac, ":", "-", -1)
		// Смотрим все мак адреса Redis	и если мак адрес конфига совпадет с мак адресом Redis, то
		// изменяем переменную found на true
		for _, redisMac := range *redisMacList {
			if configMac == redisMac {
				found = true
			}
		}
		if found {
			// Если мак адреса Redis есть в файле конфига, то смотрим следующий мак адрес Redis
			found = false
			continue
		} else {
			// Если мак адреса Redis нет в конфиге, то удаляем запись конфига с данным мак адресом
			RemoveEntry(&configMac)
		}
	}
}
