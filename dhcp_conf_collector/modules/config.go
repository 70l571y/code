package modules

import (
	"encoding/json"
	"log"
	"os"
)

var (
	config           *Config
	DHCPConfFilePath string
	LogFileName      string
	UpdateInterval   int
	RedisServer      string
	RedisPassword    string
	RedisDB          int
	PostgresServer   string
	PostgresDBName   string
	PostgresUsername string
	PostgresPassword string
)

func init() {
	// Инициализация переменных при запуске сборщика
	config = loadConfiguration("/opt/dhcp_conf_collector/config.json")
	DHCPConfFilePath = config.Collector.DHCPConfFilePath
	LogFileName = config.Collector.LogFileName
	UpdateInterval = config.Collector.UpdateInverval
	RedisServer = config.Redis.Server
	RedisPassword = config.Redis.Password
	RedisDB = config.Redis.DB
	PostgresServer = config.Postgres.Server
	PostgresDBName = config.Postgres.DBName
	PostgresUsername = config.Postgres.Username
	PostgresPassword = config.Postgres.Password
}

type Config struct {
	// Структура для удобного представления конфига сборщика
	Redis struct {
		Server   string `json:"server"`
		Password string `json:"password"`
		DB       int    `json:"db"`
	} `json:"redis"`
	Postgres struct {
		Server   string `json:"db_server"`
		DBName   string `json:"db_name"`
		Username string `json:"db_username"`
		Password string `json:"db_password"`
	} `json:"postgres"`
	Collector struct {
		LogFileName      string `json:"collector_log"`
		DHCPConfFilePath string `json:"conf_file"`
		UpdateInverval   int    `json:"update_interval"`
	} `json:"collector"`
}

func loadConfiguration(file string) *Config {
	// Ф-ия загрузки конфига по готовой структуре
	configFile, err := os.Open(file)
	defer configFile.Close()
	Check(err)
	jsonParser := json.NewDecoder(configFile)
	jsonParser.Decode(&config)
	return config
}

func Check(err error) {
	// Функция проверки ошибок
	// Если переменная err - не пустая (значит есть ошибка), значение переменной записывает в файл лога сборщика
	if err != nil {
		logFile, _ := os.OpenFile(LogFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		defer logFile.Close()
		log.SetOutput(logFile)
		log.Println(err)
	}
}
