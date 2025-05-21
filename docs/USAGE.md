# Usage

## 🚀 Startup and shutdown

```bash
docker-compose up
```
```bash
docker-compose down
```

## 📤 Sending data to Kafka `input`

```bash
docker-compose exec kafka   kafka-console-producer.sh   --bootstrap-server kafka:9092   --topic input
```

Examples of messages:
```json
{"value": 10}
{"value": 42.5}
{"foo": "bar"}  // invalid - goes to error
```

## 📥 Reading from Kafka `output`

```bash
docker-compose exec kafka   kafka-console-consumer.sh   --bootstrap-server kafka:9092   --topic output   --from-beginning   --timeout-ms 10000
```

Expected Format Outcome:
```json
{"result": -990}
{"result": -957.5}
```

## ⚠️ Reading errors from Kafka `error`

```bash
docker-compose exec kafka   kafka-console-consumer.sh   --bootstrap-server kafka:9092   --topic error   --from-beginning   --timeout-ms 10000
```

Expected Format Outcome:
```json
{"error": "{"foo":"bar"}"}
```
