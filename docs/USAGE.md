# Usage

## 🚀 Запуск и остановка

```bash
docker-compose up
```
```bash
docker-compose down
```

## 📤 Отправка данных в Kafka `input`

```bash
docker-compose exec kafka   kafka-console-producer.sh   --bootstrap-server kafka:9092   --topic input
```

Примеры сообщений:
```json
{"value": 10}
{"value": 42.5}
{"foo": "bar"}  // невалидно — попадёт в error
```

## 📥 Чтение из Kafka `output`

```bash
docker-compose exec kafka   kafka-console-consumer.sh   --bootstrap-server kafka:9092   --topic output   --from-beginning   --timeout-ms 10000
```

Ожидаемый результат формата:
```json
{"result": -990}
{"result": -957.5}
```

## ⚠️ Чтение ошибок из Kafka `error`

```bash
docker-compose exec kafka   kafka-console-consumer.sh   --bootstrap-server kafka:9092   --topic error   --from-beginning   --timeout-ms 10000
```

Пример:
```json
{"error": "{"foo":"bar"}"}
```
