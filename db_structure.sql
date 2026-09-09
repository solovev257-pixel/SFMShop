-- Структура БД для SFMShop

-- Таблица пользователей
-- Связи: нет (основная таблица)
CREATE TABLE users (
    id    SERIAL PRIMARY KEY,       -- уникальный id
    name  VARCHAR(100) NOT NULL,    -- имя обязательно
    email VARCHAR(100) UNIQUE NOT NULL -- email уникальный
);

-- Таблица товаров
-- Связи: нет (основная таблица)
CREATE TABLE products (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(200) NOT NULL,
    price    DECIMAL(10,2) NOT NULL,
    quantity INTEGER DEFAULT 0
);

-- Таблица заказов
-- Связи: orders.user_id → users.id
CREATE TABLE orders (
    id      SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id), -- заказ принадлежит пользователю
    total   DECIMAL(10,2) NOT NULL
);

-- Таблица товаров в заказах
-- Связи: order_items.order_id → orders.id
--        order_items.product_id → products.id
CREATE TABLE order_items (
    id         SERIAL PRIMARY KEY,
    order_id   INTEGER REFERENCES orders(id),   -- в каком заказе
    product_id INTEGER REFERENCES products(id), -- какой товар
    quantity   INTEGER NOT NULL                 -- сколько штук
);