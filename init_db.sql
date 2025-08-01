-- Последовательности
CREATE SEQUENCE IF NOT EXISTS pereval_id_seq;
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE SEQUENCE IF NOT EXISTS images_id_seq;

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY DEFAULT nextval('users_id_seq'),
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    fam TEXT NOT NULL,
    name TEXT NOT NULL,
    otc TEXT NOT NULL
);

-- Таблица перевалов
CREATE TABLE IF NOT EXISTS pereval_added (
    id INTEGER PRIMARY KEY DEFAULT nextval('pereval_id_seq'),
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    beauty_title TEXT,
    title TEXT NOT NULL,
    other_titles TEXT,
    connect TEXT,
    add_time TIMESTAMP NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    height INTEGER NOT NULL,
    winter TEXT,
    summer TEXT,
    autumn TEXT,
    spring TEXT,
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'pending', 'accepted', 'rejected'))
);

-- Таблица изображений
CREATE TABLE IF NOT EXISTS pereval_images (
    id INTEGER PRIMARY KEY DEFAULT nextval('images_id_seq'),
    pereval_id INTEGER NOT NULL REFERENCES pereval_added(id),
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    img BYTEA NOT NULL,
    title TEXT NOT NULL
);