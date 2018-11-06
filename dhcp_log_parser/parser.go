/*
	***Парсер логов DHCP сервера.***
Парсер работает в бесконечном цикле:
1) Получает с БД Редис байтовое смещение, определяющее место считывания файла логов
2) Получает размер файла логов DHCP сервера и сравнивает его со смещением.
Если смещение равно размеру файла (парсер дошел до конца файла), ждет одну секунду начинает работу с п/п 1
3) Построчно считывает файл логов DHCP сервера
4) Ищет строку ответа DHCP сервера клиенту - "DHCPOFFER"
5) При нахождении строки ответа - считывает ее и записывает смещение в БД Редис
6) В найденной строке ищет и записывает ip адрес ответа DHCP сервера и mac адрес клиента
с помощью регулярного выражения
7) Записывает в БД Редис mac и ip адрес клиента, в виде: ключ - mac, значение - ip
8) Переходит в п/п 1.
*/

package main

import (
	"bufio"
	"encoding/json"
	"io"
	"log"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/go-redis/redis"
)

var config *Config
var client *redis.Client
var DHCPLogFilePath string
var LogFileName string
var RedisServer string
var RedisPassword string
var RedisDB int
var CheckInterval int

func init() {
	// Инициализация переменных при запуске парсера
	config = loadConfiguration("/opt/dhcp_log_parser/config.json")
	DHCPLogFilePath = config.Parser.DHCPLogFilePath
	LogFileName = config.Parser.LogFileName
	CheckInterval = config.Parser.CheckInterval
	RedisServer = config.Redis.Server
	RedisPassword = config.Redis.Password
	RedisDB = config.Redis.DB
}

type Config struct {
	// Структура для удобного представления конфига парсера
	Redis struct {
		Server   string `json:"server"`
		Password string `json:"password"`
		DB       int    `json:"db"`
	} `json:"redis"`
	Parser struct {
		LogFileName     string `json:"parser_log"`
		DHCPLogFilePath string `json:"dhcp_log"`
		CheckInterval   int    `json:"check_interval"`
	} `json:"parser"`
}

func loadConfiguration(file string) *Config {
	// Ф-ия загрузки конфига по готовой структуре
	configFile, err := os.Open(file)
	check(err)
	jsonParser := json.NewDecoder(configFile)
	jsonParser.Decode(&config)
	return config
}

func check(err error) {
	// Функция проверки ошибок
	// Если переменная err - не пустая (значит есть ошибка), значение переменной записывает в файл лога парсера
	if err != nil {
		logFile, _ := os.OpenFile(LogFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		defer logFile.Close()
		log.SetOutput(logFile)
		log.Println(err)
	}
}

func connectToRedis() {
	// Ф-ия создает коннект к БД Редис и проверяет доступность
	// Если БД Редис - недоступна, то перепроверяет каждые 5 секунд, пока БД не будет доступна
	for {
		client = redis.NewClient(&redis.Options{
			Addr:     RedisServer,
			Password: RedisPassword,
			DB:       RedisDB,
		})
		_, err := client.Ping().Result()
		check(err)
		if err == nil {
			break
		} else {
			time.Sleep(time.Second * 5)
			continue
		}
	}
}

func worker(line string) {
	// Воркер парсит принятую строку по регулярному выражения на ip и mac адрес клиента
	// и записывает эти данные в БД Редис в виде: ключ - mac, значение - ip
	rex := regexp.MustCompile("(([^:]+):){3} ([^ ]+ ){2}(?P<ip>[^ ]+) [^ ]+ (?P<mac>[^ ]+)")
	r2 := rex.FindAllStringSubmatch(line, -1)[0]
	ip := r2[4]
	mac := strings.Replace(r2[5], ":", "-", 5)
	mac = strings.ToUpper(mac)
	client.Set(mac, ip, 0)
}

func main() {
	for {
		// Каждый раз проверяем коннект к БД Редис
		connectToRedis()
		// Если в БД Редис отсутствует запись о смещении, то выставляем смещение - "0"
		if checkOffset, _ := client.Get("file:offset").Result(); checkOffset == "" {
			client.Set("file:offset", "0", 0)
		}
		// Получаем смещение из БД Редис
		strOffset, err := client.Get("file:offset").Result()
		check(err)
		// Т.к. размер файла (с которым будем сравнивать смещение) имеет тип int64 (если запуск парсера произведен
		// с машины с архитектуров x64 то по умолчанию тип переменной fileSize - int64) - приводим переменную
		// strOffset типа string к типу данный int64:
		offset, err := strconv.ParseInt(strOffset, 10, 64)
		check(err)

		// Открываем файл логов DHCP сервера
		logFile, err := os.Open(DHCPLogFilePath)
		check(err)
		// Если возникла ошибка при открытии файла (как правило нет такого файла)
		// то парсер ждет 5 секунд и проверяет заново
		if err != nil {
			time.Sleep(time.Second * 5)
			continue
		}

		// Получаем размер файла логов DHCP сервера
		fileStat, err := logFile.Stat()
		check(err)
		fileSize := fileStat.Size()

		// DHCP сервер, чтобы файл логов не вешал много гигабайт, может при достижении размера допустим 90mb,
		// переименовывать фалй dhcpd.log в файл dhcpd.log.1 и создать новый чистый файл dhcpd.log
		// Поэтому если смещение будет больше размера файла логов, то начать считывать файл логов сначала
		if offset > fileSize {
			offset = 0
		}

		// Если смещение равно размеру файла - значит файл логов не изменился и не нужно его считывать
		if offset == fileSize {
			logFile.Close()
			time.Sleep(time.Second * time.Duration(CheckInterval))
			continue
		}

		// Инициализируем буфферный считыватель (хрен знает как перевести на русский)
		reader := bufio.NewReader(logFile)

		// Переходим (устанавливаем курсор для чтения) на число байтов смещения в файле
		// У метода file.Seek - 2 параметра (offset и whence):
		// offset - смещение
		// whence - число от 0 до 2 (0 - от начала файла, 1 - текущая позиция указателя, 2 - от конца файла)
		logFile.Seek(offset, 0)

		//Считываем файл от начала смещения до конца
		for {
			// Построчно считываем файл
			line, err := reader.ReadString('\n')
			// Ищем строчки ответа DHCP сервера клиентам, в которых есть слово - "DHCPOFFER"
			if strings.Contains(line, "DHCPOFFER") {
				// Устанавливаем текущее смещение (после находдения искомой строки)
				offset, err = logFile.Seek(0, 1)
				check(err)
				// Записываем в БД Редис смещение
				client.Set("file:offset", offset, 0)
				worker(line)
			}
			// Считываем строки до конца файла
			if err == io.EOF {
				break
			}
		}
		time.Sleep(time.Second * time.Duration(CheckInterval))
	}
}
