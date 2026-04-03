<!-- README.md -->
[![CI](https://github.com/AksenovRomanCY/kafka-processing-service/actions/workflows/ci.yml/badge.svg)](https://github.com/AksenovRomanCY/kafka-processing-service/actions/workflows/ci.yml)

# Kafka Processing Service

The application simulates the background processing of tasks:

1. **Consumer**: reads from Kafka (`input`), validates JSON with a number, sends to `error` on error, runs background tasks on success.
2. **Background tasks (Celery + Redis)**:
   - `task_1`: prints the input, adds 100, generates an exception at a random moment and, on success, passes `task_2`.
   - `task_2`: prints the input, subtracts 1000, generates an exception and, on success, sends the JSON result to Kafka `output`.
   Automatic retries are provided - no data is lost.

Documentation:
- 📦 [INSTALLATION](docs/INSTALLATION.md)
- 🚀 [USAGE](docs/USAGE.md)
- 🏗️ [ARCHITECTURE](docs/ARCHITECTURE.md)
- 🧪 [TESTING](docs/TESTING.md)
