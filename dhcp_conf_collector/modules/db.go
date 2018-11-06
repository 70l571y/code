/* Проверяем местонахождение свитча в базе
нам нужен только свитч, который в SWDB переместили на адрес
и который получил все сетевые настройки */
package modules

import (
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"
	"github.com/go-redis/redis"

	_ "github.com/lib/pq"
)

var Client     *redis.Client

func ConnectToRedis() {
	// Ф-ия создает коннект к БД Редис и проверяет доступность
	// Если БД Редис - недоступна, то перепроверяет каждые 5 секунд, пока БД не будет доступна
	for {
		Client = redis.NewClient(&redis.Options{
			Addr:     RedisServer,
			Password: RedisPassword,
			DB:       RedisDB,
		})
		_, err := Client.Ping().Result()
		Check(err)

		if err == nil {
			break
		} else {
			time.Sleep(time.Second * 5)
			continue
		}
	}
}

func GetProductionSwitches(macList *[]string) *[]string {
	productionSwitches := make([]string, 0, len(*macList))
	psqlInfo := fmt.Sprintf("postgres://%s:%s@%s/%s", PostgresUsername, PostgresPassword, PostgresServer, PostgresDBName)

	db, err := sql.Open("postgres", psqlInfo)
	Check(err)
	defer db.Close()

	for _, mac := range *macList {
		switchesSqlQuery := fmt.Sprintf("SELECT allocation_id FROM switches where switch_data @>'{\"mac\": \"%s\"}';", mac)
		switchesRows, err := db.Query(switchesSqlQuery)
		Check(err)
		for switchesRows.Next() {
			var line string
			err = switchesRows.Scan(&line)
			Check(err)
			if line == "1" {
				productionSwitches = append(productionSwitches, mac)
			}
		}

		err = switchesRows.Err()
		Check(err)
		switchesRows.Close()
	}
	return &productionSwitches
}

func GetNetworkSettings(mac *string) (ipAddress, networkAdress, gatewayAddress, networkMask string) {
	var (
		IP         string
		Subnet     string
		SubnetAddr string
		Gateway    string
		SubnetID   string
		Mask       string
	)

	*mac = strings.ToUpper(*mac)
	*mac = strings.Replace(*mac, ":", "-", -1)

	psqlInfo := fmt.Sprintf("postgres://%s:%s@%s/%s", PostgresUsername, PostgresPassword, PostgresServer, PostgresDBName)
	db, err := sql.Open("postgres", psqlInfo)
	Check(err)
	defer db.Close()

	// Получаем IP адерс свитча из БД SWDB по мак адресу
	sqlGetIP := fmt.Sprintf("select switch_data from switches where switch_data @>'{\"mac\": \"%s\"}';", *mac)
	switchData, err := db.Query(sqlGetIP)
	defer switchData.Close()
	Check(err)
	for switchData.Next() {
		var line string
		err = switchData.Scan(&line)
		Check(err)

		type IPADDR struct {
			IPAddr string `json:"ip"`
		}
		text := []byte(line)

		var t IPADDR
		err := json.Unmarshal(text, &t)
		Check(err)
		IP = t.IPAddr
	}

	// Получаем ID подсети
	sqlGetSubnetID := fmt.Sprintf("select subnet_id from switches where switch_data @>'{\"mac\": \"%s\"}';", *mac)
	getSubnetID, err := db.Query(sqlGetSubnetID)
	defer getSubnetID.Close()
	Check(err)
	for getSubnetID.Next() {
		var line string
		err = getSubnetID.Scan(&line)
		Check(err)
		SubnetID = line
	}

	// Получаем адрес сети
	sqlGetNetworkAddress := fmt.Sprintf("select network from subnets where id=%s;", SubnetID)
	getNetworkAddress, err := db.Query(sqlGetNetworkAddress)
	defer getNetworkAddress.Close()
	Check(err)
	for getNetworkAddress.Next() {
		var line string
		err = getNetworkAddress.Scan(&line)
		Check(err)
		Subnet = line
		if strings.Contains(Subnet, "/") {
			networkIndex := strings.Index(Subnet, "/")
			SubnetAddr = Subnet[:networkIndex]
		}
	}

	// Получаем IP адрес шлюза
	sqlGetGatewayAddress := fmt.Sprintf("select gw from subnets where id=%s;", SubnetID)
	getGatewayAddress, err := db.Query(sqlGetGatewayAddress)
	defer getGatewayAddress.Close()
	Check(err)
	for getGatewayAddress.Next() {
		var line string
		err = getGatewayAddress.Scan(&line)
		Check(err)
		Gateway = line
	}

	// Получаем маску сети
	if strings.Contains(Subnet, "/") { // Ищем префикс /24 у адреса подсети формата - 192.168.96.0/24
		onesIndex := strings.Index(Subnet, "/") // Получаем индекс префикса
		strOnes := Subnet[onesIndex+1:]         // Получаем индекс префикса (типа string)
		ones, err := strconv.Atoi(strOnes)      // Конвертируем значение префикса в тип int
		Check(err)
		hexMask := net.CIDRMask(ones, 32)                    // Получаем маску подсети типа "ffffff00"
		sliceMask, err := hex.DecodeString(hexMask.String()) // Получаем слайс формата [255 255 255 0]
		Check(err)
		if len(sliceMask) == 4 {
			Mask = fmt.Sprintf("%d.%d.%d.%d", sliceMask[0], sliceMask[1], sliceMask[2], sliceMask[3])
		}
	}

	return IP, SubnetAddr, Gateway, Mask
}
