# Testing

## ✅ Unit Tests

### Запуск:

```bash
pytest
````

### Что покрыто:

* **Валидация JSON** в `handle_message`:

  * валидный payload
  * некорректный JSON
  * отсутствие поля `value` или `null`
  * нечисловое значение
  * float и отрицательные числа

* **Логика Celery-тасков** `task_1` и `task_2`:

  * успешный путь (`value + 100 → task_2.delay`; `value - 1000 → send_to_kafka`)
  * ветка исключения (распаковка `random_fail`)

* **Подмена всех вызовов** `send_to_kafka` на заглушку

## 🔬 E2E (docker-compose)

```bash
docker-compose up --build --abort-on-container-exit
```

Проверка:
* Все сервисы запускаются
* Консольные продьюсер / консьюмер работают корректно
