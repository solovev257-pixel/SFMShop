# SFMShop

Интернет-магазин для продажи товаров.

## Описание
Проект для изучения Python на практике.

## Настройка окружения

Используется Python 3.13. Код с `asyncio.TaskGroup` требует Python 3.11 или новее.

1. Создать виртуальное окружение в папке проекта:

        python -m venv venv

2. Включить его:

        .\venv\Scripts\Activate.ps1   # Windows PowerShell
        source venv/bin/activate      # Linux / macOS

   Когда окружение включено, в начале строки терминала видно `(venv)`.

3. Поставить зависимости:

        python -m pip install -r requirements.txt
        python -m pip check

4. Проверить, что всё встало:

        python -c "import fastapi, psycopg2, redis, pika, pymongo, sqlalchemy; print('ok')"
        python -m pytest tests -q --cov=src --cov-report=term-missing

Выключить окружение: `deactivate`.

## Зависимости

В `requirements.txt` лежат только библиотеки, которые проект использует напрямую.
Новые прямые зависимости дописываются вручную. `requirements-lock.txt` содержит
прежний снимок окружения, актуальная установка выполняется по `requirements.txt`.

## Конфигурация

Если `.env` ещё отсутствует, скопировать `.env.example` в `.env` и заполнить пароли,
`JWT_SECRET_KEY` и при необходимости `LLM_API_KEY`. Существующий `.env` сохраняется.
`.env` исключён из Git и Docker-образа. Все настройки основного приложения проходят
через `Settings` в `src/core/config.py`. Переменные процесса имеют приоритет над `.env`.
Пустой `SFMShop_ENV_FILE` отключает чтение файла, это используется в автотестах и CI.
Для локального Python нужны запущенные PostgreSQL и Redis с таблицами из `docker/init.sql`.
В Compose адреса БД, кеша и очереди задаются именами сервисов.

## Запуск в Docker

Из корня проекта с заполненным `.env` выполнить

```powershell
docker compose --env-file .env -f docker/docker-compose.yml up -d --build --wait
```

Для изолированной учебной проверки с публичными тестовыми значениями используется
отдельное имя проекта

```powershell
docker compose --env-file .env.example -f docker/docker-compose.yml -p sfmshop-mentor up -d --build --wait
python scripts/check_deployment.py
```

API доступен по `http://127.0.0.1:8000/docs`, админстраница по `/admin`.
`/health/live` проверяет работу процесса, `/health/ready` проверяет PostgreSQL и Redis.
При отказе Redis приложение продолжает обслуживать запросы через БД.
Compose поднимает API, PostgreSQL, Redis, RabbitMQ, обработчик очереди и MongoDB для его логов.
Фоновые обработчики писем и отчётов пока имитируют работу записью в лог.

Для запуска API непосредственно из Python используется

```powershell
python -m uvicorn src.api.main:app --reload
```

В PyCharm выбрать интерпретатор `venv/Scripts/python.exe` и модуль `uvicorn`
с параметрами `src.api.main:app --reload`, рабочая папка — корень SFMShop.

## Тестирование и CI

Автотесты используют вымышленные данные и подменяют внешнюю модель, БД, кеш и очередь.
`.coveragerc` включает все модули `src`, в том числе папки без `__init__.py`, и требует
не менее 81% покрытия строк. Основные модели `Product`, `User`, `Order` проверяются
в `tests/test_models.py`, помощник — в `tests/test_support.py`.

Workflow `.github/workflows/ci.yml` запускает тесты, проверку типов, линтер и проверку
развёртывания контейнеров при push и pull request в main. Линтер ищет ошибки в коде.
Job `deploy` запускает учебный стек на GitHub runner и выполняет сквозную HTTP-проверку.
Публикация на внешний сервер требует отдельной настройки выбранного хостинга.

Подробности находятся в `docs/testing_approach.md`, `docs/deployment.md`
и `docs/infrastructure_plan.md`. Отдельный учебный `order-service/` использует внешний
payment-service и имеет собственную инструкцию запуска в `order-service/README.md`.
