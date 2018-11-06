// Агент принимает параметры от заббикса и передает их RabbitMQ (брокеру сообщений)

package main

import (
	"fmt"
	"log"
	"os"
	"github.com/streadway/amqp"
)

var (
	rabbitMessage string
	logFile       *os.File
)

const (
	rabbitServer = "localhost"
	rabbitPort   = "5672"
	rabbitUser   = "agent"
	rabbitPass   = "b5f0d27764fe191ebe0dcd62d317dad4"
)

func init() {
	logFile, _ = os.OpenFile("/tmp/botTelegramAgent.log", os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
	log.SetOutput(logFile)
}

func check(err error, msg string) {
	if err != nil {
		log.Fatalf("%s: %s\n", msg, err)
	}
}

func sendRabbitMsg(msg string) {
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
	check(err, "Failed to declare a queue")

	body := msg
	err = ch.Publish(
		"",     // exchange
		q.Name, // routing key
		false,  // mandatory
		false,  // immediate
		amqp.Publishing{
			ContentType: "text/plain",
			Body:        []byte(body),
		})
	check(err, "Failed to publish a message")
	log.Printf("Сообщение от Заббикса передано брокеру RabbitMQ: %s", body)
	logFile.Close()
}

func main() {
	//log.Println("Запущен агент!")
	argsList := os.Args
	if len(argsList) > 4 {
		/*
		Заббикс запускает агента с аргументами, вида:
		telegram theme apc1000-1.bunker.krsk.m.krw.rzd PROBLEM NODE
		telegram theme apc1000-1.bunker.krsk.m.krw.rzd OK NODE
		незабываем что нулевой аргумент это название самого исполняемого файла
		 */
		rabbitMessage = fmt.Sprintf("%s %s", argsList[3], argsList[4])
		log.Printf("Получено сообщение от Заббикса: %s", rabbitMessage)
		sendRabbitMsg(rabbitMessage)
	}
}
