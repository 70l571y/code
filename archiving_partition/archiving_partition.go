package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

const (
	configFilePath  = "/opt/archiving_partition/config.json"
	logFileName     = "/var/log/zabbix-scripts/archiving.log"
	createPartition = "ALTER TABLE %s ADD PARTITION (PARTITION %s VALUES LESS THAN (UNIX_TIMESTAMP(\"%s\")));"
	dropPartition   = "ALTER TABLE %s DROP PARTITION %s;"
)

var (
	config               *conf
	dbHost               string
	dbName               string
	dbUser               string
	dbPass               string
	dbPath               string
	raidPath             string
	fastRaidPath         string
	firstStartHour       int
	secondStartHour      int
	startMinute          int
	daysBeforeRemoval    int
	partitionTables      []string
	removeTables         []string
	nowTime              time.Time
	tomorrowDate         time.Time
	removalDate          time.Time
	newPartition         string
	oldPartition         string
	removalPartition     string
	timestamp            string
	oldPartitionFileName string
	query                string
	historyTablePath     string
	filename             string
	oldPartitionFiles    *[]string
	deleteFiles          *[]string
	moveFiles            *[]string
	symFiles             *[]string
)

func init() {
	config = loadConfiguration(configFilePath)

	dbHost = config.DB.Host
	dbName = config.DB.Name
	dbUser = config.DB.User
	dbPass = config.DB.Pass
	dbPath = config.Path.DB
	raidPath = config.Path.Raid
	fastRaidPath = config.Path.FastRaid
	firstStartHour = config.Settings.FirstStartHour
	startMinute = config.Settings.StartMinute
	secondStartHour = config.Settings.SecondStartHour
	daysBeforeRemoval = config.Settings.DaysBeforeRemoval
	partitionTables = config.PartitionTables
	removeTables = config.RemoveTables
}

type conf struct {
	// Структура для удобного представления конфига сборщика
	DB struct {
		Host string `json:"Host"`
		Name string `json:"Name"`
		User string `json:"User"`
		Pass string `json:"Pass"`
	} `json:"DB"`
	Path struct {
		DB       string `json:"DB"`
		Raid     string `json:"Raid"`
		FastRaid string `json:"fast_raid"`
	} `json:"Path"`
	Settings struct {
		FirstStartHour    int `json:"firstStartHour"`
		SecondStartHour   int `json:"secondStartHour"`
		StartMinute       int `json:"startMinute"`
		DaysBeforeRemoval int `json:"daysBeforeRemoval"`
	}
	PartitionTables []string `json:"partition_tables"`
	RemoveTables    []string `json:"remove_tables"`
}

func loadConfiguration(filePath string) *conf {
	// Ф-ия загрузки конфига по готовой структуре
	configFile, err := os.Open(filePath)
	if err != nil {
		log.Println(err)
	}
	jsonParser := json.NewDecoder(configFile)
	jsonParser.Decode(&config)
	return config
}

func recordDB(query *string) {
	mysqlInfo := fmt.Sprintf("%s:%s@tcp(%s)/%s", dbUser, dbPass, dbHost, dbName)
	for {
		db, _ := sql.Open("mysql", mysqlInfo)
		err := db.Ping()
		if err != nil {
			time.Sleep(time.Second * 5)
			continue
		} else {
			create, err := db.Query(*query)
			if err != nil {
				log.Println(err)
			}
			create.Close()
			db.Close()
			log.Printf("Выполнение запроса - '%s'", *query)
			break
		}
	}
}

func findFiles(pattern, path *string) *[]string {
	var files []string
	filepath.Walk(*path, func(path string, f os.FileInfo, _ error) error {
		if !f.IsDir() {
			r, err := regexp.MatchString(*pattern, f.Name())
			if err == nil && r {
				files = append(files, f.Name())
			}
		}
		return nil
	})
	return &files
}

func moveTables(files *[]string, path, path2 *string) {
	for _, file := range *files {
		if err := exec.Command("mv", *path+file, *path2).Run(); err != nil {
			log.Println(err)
			log.Printf("Невозможно переместить файл '%s' в папку '%s'", file, *path2)
		}
	}
}

func deleteTables(files *[]string, path *string) {
	for _, file := range *files {
		if err := exec.Command("rm", *path+file).Run(); err != nil {
			log.Println(err)
			log.Printf("Невозможно удалить файл - '%s'", file)
		}
	}
}

func createSymlinks(files *[]string, path, path2 *string) {
	for _, file := range *files {
		if err := exec.Command("ln", "-s", *path+file, *path2).Run(); err != nil {
			log.Println(err)
			log.Printf("Невозможно создать символьную ссылку на '%s%s'", *path2, file)
		}
	}
}

func main() {

	// Открываем файл логов
	logFile, _ := os.OpenFile(logFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
	defer logFile.Close()
	log.SetOutput(logFile)

	for {
		// Получаем текущее время
		nowTime = time.Now()
		// Если текущий час равен часу запуска из конфига, то начинаем работу, иначе ждем и перепроверяем время
		if (nowTime.Hour() == firstStartHour) && (nowTime.Minute() == startMinute) ||
			(nowTime.Hour() == secondStartHour) && (nowTime.Minute() == startMinute) {
			// Получаем имена файлов партиция и unix timestamp (нужен для создания партиций)
			tomorrowDate = nowTime.AddDate(0, 0, 1)
			removalDate = nowTime.AddDate(0, 0, -daysBeforeRemoval)

			newPartition = fmt.Sprintf("p%d_%02d_%02d_%02d", tomorrowDate.Year(), tomorrowDate.Month(), tomorrowDate.Day(), tomorrowDate.Hour())
			oldPartition = fmt.Sprintf("p%d_%02d_%02d_%02d", nowTime.Year(), nowTime.Month(), nowTime.Day(), nowTime.Hour())
			removalPartition = fmt.Sprintf("p%d_%02d_%02d_%02d", removalDate.Year(), removalDate.Month(), removalDate.Day(), removalDate.Hour())
			timestamp = fmt.Sprintf("%d-%02d-%02d %02d:00:00", tomorrowDate.Year(), tomorrowDate.Month(), tomorrowDate.Day(), tomorrowDate.Hour())

			log.Println("\n\n[x] Удаление старых партиций из БД (симлинков):")
			for _, table := range removeTables {
				// Получаем имя партиций для удаления (в конфиге указывается за сколько дней удалять партиции)
				oldPartitionFileName = fmt.Sprintf("_zabbix_%s_P_%s", table, removalPartition)
				// Ищем партиции для удаления на диске БД
				oldPartitionFiles = findFiles(&oldPartitionFileName, &dbPath)
				if *oldPartitionFiles != nil {
					// Удаляем с БД старые партиции
					query = fmt.Sprintf(dropPartition, table, removalPartition)
					recordDB(&query)
				} else {
					log.Printf("[x] В БД отсутствует партиция - %s", oldPartitionFileName)
					continue
				}
			}

			log.Println("\n\n[x] Создание новых партиций:")
			for _, table := range partitionTables {
				query = fmt.Sprintf(createPartition, table, newPartition, timestamp)
				recordDB(&query)
			}

			log.Println("\n\n[x] Остановка БД")
			if err := exec.Command("service", "mysql", "stop").Run(); err != nil {
				log.Println(err)
				log.Println("Невозможно оставновить БД")
				continue
			}

			// Удаление старых партиций (если они есть)
			for _, table := range removeTables {
				if table == "history" || table == "history_uint" {
					historyTablePath = fastRaidPath + table + "/"
					filename = fmt.Sprintf("_zabbix_%s_P_%s", table, removalPartition)
					deleteFiles = findFiles(&filename, &historyTablePath)
					if deleteFiles != nil {
						log.Printf("[x] Удаление таблицы '%s' с дискового массива", table)
						deleteTables(deleteFiles, &historyTablePath)
					} else {
						log.Printf("[x] В каталоге %s - отсутствует партиция: %s", historyTablePath, filename)
						continue
					}
				} else {
					tablePath := raidPath + table + "/"
					filename = fmt.Sprintf("_zabbix_%s_P_%s", table, removalPartition)
					deleteFiles = findFiles(&filename, &tablePath)
					if deleteFiles != nil {
						log.Printf("[x] Удаление таблицы '%s' с дискового массива", table)
						deleteTables(deleteFiles, &tablePath)
					} else {
						log.Printf("[x] В каталоге %s - отсутствует партиция: %s", tablePath, filename)
						continue
					}
				}
			}

			// Перемещение новых партиций
			for _, table := range partitionTables {
				filename = fmt.Sprintf("_zabbix_%s_P_%s", table, oldPartition)
				moveFiles = findFiles(&filename, &dbPath)

				if moveFiles != nil {
					if table == "history" || table == "history_uint" {
						historyTablePath := fastRaidPath + table + "/"
						log.Printf("[x] Перемещение таблицы '%s' на дисковый массив\n", table)
						moveTables(moveFiles, &dbPath, &historyTablePath)
						symFiles = findFiles(&filename, &historyTablePath)
						log.Printf("[x] Создание символьной ссылки для таблицы: '%s'\n", table)
						if *symFiles != nil {
							createSymlinks(symFiles, &historyTablePath, &dbPath)
						} else {
							log.Printf("Нет партиции %s в папке %s", filename, raidPath+table+"/")
							continue
						}
					} else {
						log.Printf("[x] Перемещение таблицы '%s' на дисковый массив\n", table)
						tablesPath := raidPath + table + "/"
						moveTables(moveFiles, &dbPath, &tablesPath)
						log.Printf("[x] Создание символьной ссылки для таблицы: '%s'\n", table)
						symFiles = findFiles(&filename, &tablesPath)
						if symFiles != nil {
							createSymlinks(symFiles, &tablesPath, &dbPath)
						} else {
							log.Printf("Нет партиции %s в папке %s", filename, tablesPath)
							continue
						}
					}
				} else {
					log.Printf("Нет такого файла '%s' в папке '%s'", filename, dbPath)
				}
			}

			log.Println("[x] Запуск БД")
			if err := exec.Command("service", "mysql", "start").Run(); err != nil {
				log.Println(err)
				log.Println("Невозможно запустить БД")
			}

			time.Sleep(time.Second * 30)
			continue
		} else {
			time.Sleep(time.Second * 30)
			continue
		}
	}
}
