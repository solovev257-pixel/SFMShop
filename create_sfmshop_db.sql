CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL
);

INSERT INTO users (name, email) VALUES
    ('Иван', 'ivan@test.ru'),
    ('Мария', 'maria@test.ru'),
    ('Петр', 'petr@test.ru')
ON CONFLICT DO NOTHING;

INSERT INTO products (name, price, quantity) VALUES
    ('Ноутбук', 50000.00, 10),
    ('Мышь', 1500.00, 20),
    ('Клавиатура', 3000.00, 15),
    ('Монитор', 30000.00, 5),
    ('Наушники', 5000.00, 8)
ON CONFLICT DO NOTHING;