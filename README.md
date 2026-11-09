# SFMShop

Интернет-магазин для продажи товаров.

## Описание
Проект для изучения Python на практике.

## Настройка окружения

Нужен Python 3.10 или новее.

1. Создать виртуальное окружение в папке проекта:

        python -m venv .venv

2. Включить его:

        .venv\Scripts\activate        # Windows
        source .venv/bin/activate     # Linux / macOS

   Когда окружение включено, в начале строки терминала видно `(.venv)`.

3. Поставить зависимости:

        pip install -r requirements.txt

4. Проверить, что всё встало:

        python -c "import fastapi, psycopg2, redis, pika, pymongo, sqlalchemy; print('ok')"
        python -m pytest tests/ -v

Выключить окружение: `deactivate`.

## Зависимости

В `requirements.txt` лежат только библиотеки, которые проект использует напрямую.
Точные версии всех пакетов, включая зависимости зависимостей, записаны в
`requirements-lock.txt`. Если нужно повторить окружение один в один:

    pip install -r requirements-lock.txt

Добавили новую библиотеку — допишите её в `requirements.txt` и обновите слепок:

    pip install имя_пакета
    pip freeze > requirements-lock.txt
