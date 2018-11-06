package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"github.com/streadway/amqp"
	"github.com/Syfaro/telegram-bot-api"
	"time"
)

var (
	rabbitMessage string // Сообщение от кролика

	deviceName      string                     // Доменное имя устройства
	deviceStatus    string                     // Статус устройства
	listDownDevices  = make(map[string]string) // Карта упавших устройств (ключ - имя, значение - статус)
	listOfDevices    = make(map[string]string) // Карта всех сообщений от заббикса для буфера

	counter int // Счетчик для выдова списка устройств
	buffCounter int // Счетчик для буфера отправки сообщений

	msg string // Сообщение боту
	buffMsg string // буфер сообщений

	zabbixMsg = make([]string, 2) // Приходящее сообщение от кролика (Аргумент, который передает агенту заббикс, и который агент отслывает кролику)

	logFile *os.File // Собственно файл логов
)

const (
	rabbitServer = "localhost"
	rabbitPort   = "5672"
	rabbitUser   = "agent"
	rabbitPass   = "pass"

	// глобальная константа в которой храним токен
	telegramBotToken = "mytoken"
	// глобальная константа в которой храним id чата (Monitoring devices - KRW.RZD)
	chatID = -291897819
)

func init() {
	logFile, _ = os.OpenFile("/tmp/botTelegram.log", os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
	log.SetOutput(logFile)
	log.Println("Запуск алерт бота!")

	//zabbixMsg = make([]string, 2)
	//listDownDevices = make(map[string]string)
}

func check(err error, msg string) {
	if err != nil {
		log.Fatalf("%s: %s", msg, err)
		panic(fmt.Sprintf("%s: %s", msg, err))
	}
}

func sendRabbitMsg(msg string) {
	// Если не будет связи с сервером телеграма, то бот будет каждые 10 секунд к нему пробовать подключаться
	for {
		bot, err := tgbotapi.NewBotAPI(telegramBotToken)
		if err != nil {
			log.Fatalln("Невозможно подключиться к серверу Telegram")
			time.Sleep(time.Second * 10)
			continue
		}
		bot.Send(tgbotapi.NewMessage(chatID, msg))
		break
	}
}

func receveRabbitMsg() {
	conn, err := amqp.Dial(fmt.Sprintf("amqp://%s:%s@%s:%s/", rabbitUser, rabbitPass, rabbitServer, rabbitPort))
	check(err, fmt.Sprintf("Невозможно подключиться к брокеру RabbitMQ (%s:%s)", rabbitServer, rabbitPort))
	defer conn.Close()

	ch, err := conn.Channel()
	check(err, "Невозможно открыть канал у брокера RabbitMQ")
	defer ch.Close()

	q, err := ch.QueueDeclare(
		"devices", // name
		false,     // durable
		false,     // delete when unused
		false,     // exclusive
		false,     // no-wait
		nil,       // arguments
	)
	check(err, "Ошибка про объявлении очереди у брокера RabbitMQ")

	msgs, err := ch.Consume(
		q.Name, // queue
		"",     // consumer
		true,   // auto-ack
		false,  // exclusive
		false,  // no-local
		false,  // no-wait
		nil,    // args
	)
	check(err, "Ошибка при регистрации клиента у брокера RabbitMQ")

	forever := make(chan bool)

	go func() {
		for d := range msgs {
			// Получаем сообщение от кролика (байт символов) и преобразуем в строку
			rabbitMessage = fmt.Sprintf("%s", d.Body)
			// разделяем строку на аргументы
			zabbixMsg = strings.Split(rabbitMessage, " ")
			// аргументов должно быть более 1 (имя устройства и статус)
			if len(zabbixMsg) > 1 {
				deviceName = zabbixMsg[0]
				deviceStatus = zabbixMsg[1]

				// проверяем статус ("OK", "Problem")
				if deviceStatus == "OK" || deviceStatus == "Ok" || deviceStatus == "ok" {
					listOfDevices[deviceName] = "Ожил"
					//sendRabbitMsg(fmt.Sprintf("%s - Ожил", *deviceName))
					// Если статус "ОК", то необходимо проверить устройство в списке упавших
					//если оно есть в списке, то его удалить оттуда
					if _, ok := listDownDevices[deviceName]; ok {
						delete(listDownDevices, deviceName)
					}
				} else {
					//sendRabbitMsg(fmt.Sprintf("%s - Упал", *deviceName))
					listOfDevices[deviceName] = "Упал"
					listDownDevices[deviceName] = "Упал"
				}
			}
		}
	}()
	<-forever
}

func printListDownDevices() {
	// составляем список лежачих устройств
	counter = 0
	msg = ""

	if len(listDownDevices) > 0 {
		msg = fmt.Sprintf("Всего лежачих устройств - %dшт:\n", len(listDownDevices))
		for devName := range listDownDevices {
			counter++
			msg += fmt.Sprintf("%s\n", devName)
			if counter == 20 { // формируем сообщения не более 20 строк
				sendRabbitMsg(msg)
				counter = 0
				msg = ""
			}
		}
		sendRabbitMsg(msg)
		//sendRabbitMsg("Просмотреть список упавших устройств Вы можете командой '/list', а кол-во  - '/count'")
	} else {
		msg = "Нет упавших устройств!"
		sendRabbitMsg(msg)
	}



	//	if len(listDownDevices) > 0 {
	//		msg = fmt.Sprintf("Всего лежачих устройств - %dшт:\n", len(listDownDevices))
	//		for devName := range listDownDevices {
	//			counter++
	//			msg += fmt.Sprintf("%s\n", devName)
	//			if counter == 20 { // формируем сообщения не более 20 строк
	//				sendRabbitMsg(msg)
	//				counter = 0
	//				msg = ""
	//			}
	//		}
	//		sendRabbitMsg(msg)
	//	} else {
	//		msg = "Список упавших устройств - пуст!"
	//		sendRabbitMsg(msg)
	//	}
}

func printDeviceStatus() {
	for {
		if len(listOfDevices) > 0 {
			//if len(listOfDevices) > 100 {
			//	msg = "Внимаине!!!\nПоступило более 100 сообщений боту о статусе устройств!!!\nПросмотреть список упавших устройств Вы можете командой '/list', а кол-во  - '/count'"
			//	sendRabbitMsg(msg)
			//	time.Sleep(time.Second * 5)
			//	msg = ""
			//	continue
			//}
			for devName, devStatus := range listOfDevices {
				buffCounter++
				delete(listOfDevices, devName)
				buffMsg += fmt.Sprintf("%s - %s\n", devName, devStatus)
				if buffCounter == 20 {
					sendRabbitMsg(buffMsg)
					buffCounter = 0
					buffMsg = ""
				}
			}
			sendRabbitMsg(buffMsg)
			//sendRabbitMsg("Просмотреть список упавших устройств Вы можете командой '/list', а кол-во  - '/count'")
			buffCounter = 0
			buffMsg = ""
		}
		time.Sleep(time.Second * 5)
	}
}

func main() {
	// Запускаем в фоне сборщик сообщений от кролика
	go receveRabbitMsg()

	// Выводим статус устройств в телеграм канал
	go printDeviceStatus()

	bot, err := tgbotapi.NewBotAPI(telegramBotToken)
	check(err, "Невозможно подключиться к серверу Telegram")
	// u - структура с конфигом для получения апдейтов
	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	// используя конфиг u создаем канал в который будут прилетать новые сообщения
	updates, err := bot.GetUpdatesChan(u)
	check(err, "Невозможно создать go-канал, в который прилетают новые сообщения!")

	// в канал updates прилетают структуры типа Update
	// вычитываем их и обрабатываем
	for update := range updates {
		// универсальный ответ на любое сообщение
		//msg = "Неизвестная команда!\nДля помощи по командам напишите мне '/help' или 'помощь'!"
		if update.Message == nil {
			continue
		}
		// свитч на обработку комманд
		// комманда - сообщение, начинающееся с "/"
		switch update.Message.Command() {
		case "list":
			printListDownDevices()
		case "count":
			if len(listDownDevices) > 0 {
				msg = fmt.Sprintf("Всего лежачих устройств - %dшт", len(listDownDevices))
				sendRabbitMsg(msg)
			} else {
				msg = "Нет упавших устройств!"
				sendRabbitMsg(msg)
			}
		case "help":
			msg = "Я знаю команды:\n /list - список упавших свитчей\n /count - кол-во уавших устройств"
			sendRabbitMsg(msg)
		}
		//sendRabbitMsg(msg)
	}
}
