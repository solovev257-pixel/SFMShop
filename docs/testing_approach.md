# Тестирование в SFMShop

Тесты лежат в папке `tests/` и запускаются командой:

    python -m pytest tests/ -v

Сейчас их 23, все проходят. Ни один тест не ходит в настоящую базу, Redis или RabbitMQ,
поэтому всё запускается за пару секунд без поднятых сервисов.

## Какие тесты есть

**tests/test_models.py** — тесты моделей. Проверяю, что Product, User и Order создаются
с правильными полями, что товар с отрицательной ценой и пользователь с почтой без `@`
выбрасывают ValueError, и что работают методы: `to_json()` у пользователя,
`calculate_total()`, `len()` и `in` у заказа.

**tests/test_utils.py** — тесты функций расчёта из `src/utils/calculations.py`:
скидка, сумма позиции, стоимость доставки и бесплатная доставка от 5000 рублей
(отдельно проверил границу: 4999 — платно, 5000 — уже бесплатно).

**tests/test_api.py** — тесты эндпоинтов `GET /api/v1/products` и `POST /api/v1/orders`.
База, кэш и очередь в них подменены моками, проверяю код ответа и данные в ответе.

## Покрытие

Покрытие смотрю через pytest-cov:

    python -m pytest --cov=src --cov-report=term-missing

Модели покрыты хорошо: user.py — 100%, product.py — 92%, order.py — 85%.
По всему src процент ниже, потому что там много старых учебных файлов и бенчмарков,
их тестировать смысла нет. Главное — покрыта бизнес-логика.

## Как организованы тесты

Повторяющиеся объекты создаю через фикстуры. Например, `sample_order` собирается
из фикстур `sample_user` и `sample_product`, поэтому в каждом тесте не нужно заново
создавать пользователя и товар.

Если функцию надо проверить на разных числах, использую параметризацию:

    @pytest.mark.parametrize("order_total, delivery_cost, expected", [
        (4999, 400, 400),
        (5000, 400, 0),
        (12000, 700, 0),
    ])
    def test_calculate_delivery_discount(order_total, delivery_cost, expected):
        assert calculate_delivery_discount(order_total, delivery_cost) == expected

## Какие техники применял

**TDD.** Функцию `calculate_delivery_discount` писал по циклу красный — зелёный — рефакторинг:
сначала тест упал с ImportError, потом написал простой `if`, тест прошёл, потом вынес
порог 5000 в константу `FREE_SHIPPING_THRESHOLD`, тесты остались зелёными.

**Моки.** Использую unittest.mock. Патч ставлю там, где имя используется, а не где
объявлено: `products.py` импортирует `get_products_cached` к себе, поэтому патчу именно его:

    @patch("src.api.routes.products.get_products_cached", new_callable=AsyncMock)
    def test_get_products(mock_get_cached):
        mock_get_cached.return_value = (page, True)
        response = client.get("/api/v1/products")
        assert response.status_code == 200

**Подмена зависимостей FastAPI.** Репозиторий базы и текущий пользователь приходят
в эндпоинты через Depends, поэтому в тестах подменяю их через `app.dependency_overrides`.
После каждого теста подмены очищаются, чтобы тесты не мешали друг другу.
