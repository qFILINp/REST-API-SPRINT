# API для горных перевалов (REST_API_SPRINT)

## Описание проекта

Данный проект представляет собой REST API для работы с данными о горных перевалах. 
API предоставляет следующие возможности:

- Добавление новых перевалов
- Получение информации о существующих перевалах
- Обновление данных о перевалах
- Поиск перевалов по email пользователя

API реализовано на Flask с использованием PostgreSQL в качестве базы данных.
Документация доступна через Swagger UI.

## Требования

Для запуска проекта необходимо:

- Python 3.8+
- PostgreSQL 12+
- Установленные зависимости из requirements.txt

## Установка и настройка

1. Клонируйте репозиторий:

    ``` bash
     git clone https://github.com/qFILINp/REST-API-SPRINT.git
     cd REST-API-SPRINT
     ```
2. Создайте и активируйте виртуальное окружение:

    ``` bash
    python -m venv venv
    source venv/bin/activate  # Linux/MacOS
    venv\Scripts\activate  # Windows
    ```
3. Установите зависимости:
    ``` bash
    pip install -r requirements.txt
    ```
4. Настройте базу данных PostgreSQL:

    Создайте файл .env в корне проекта со следующими параметрами:

    ``` ini
    FSTR_DB_HOST=localhost
    FSTR_DB_PORT=5432
    FSTR_DB_NAME=pereval
    FSTR_DB_LOGIN=pereval_user
    FSTR_DB_PASS=simplepass123
    ```
5. Инициализируйте базу данных:

    ``` bash
    psql -U postgres -f init_db.sql
    ```
## Запуск приложения

Для запуска API выполните:

``` bash
python app.py
```

Приложение будет доступно по адресу: http://localhost:5000

Swagger-документация доступна по адресу: http://localhost:5000/swagger/

## Документация API

1. Добавление нового перевала

    Endpoint: POST /pereval/submitData

    Пример запроса:

    ``` json
    {
      "beauty_title": "пер. Корженевского",
      "title": "Перевал Корженевского",
      "other_titles": "пер. Корж.",
      "connect": "Соединяет ледники Корженевского и Москвина",
      "add_time": "2023-09-22T13:18:13",
      "user": {
        "email": "user@example.com",
        "fam": "Иванов",
        "name": "Петр",
        "otc": "Сергеевич",
        "phone": "+79991234567"
      },
      "coords": {
        "latitude": 55.7558,
        "longitude": 37.6176,
        "height": 100
      },
      "level": {
        "winter": "1A",
        "summer": "1B",
        "autumn": "2A",
        "spring": "2B"
      }
    }
    ```

    Пример ответа:

    ```  json
    {
      "status": 200,
      "message": "Перевал успешно добавлен",
      "id": 123
    }
    ```

2. Получение информации о перевале по ID

    Endpoint: GET /pereval/submitData/<int:pass_id>

    Пример ответа:

    ``` json
    {
      "status": 200,
      "message": "Данные успешно получены",
      "data": {
        "id": 123,
        "beauty_title": "пер. Корженевского",
        "title": "Перевал Корженевского",
        "other_titles": "пер. Корж.",
        "connect": "Соединяет ледники Корженевского и Москвина",
        "add_time": "2023-09-22T13:18:13",
        "status": "new",
        "coords": {
          "latitude": 55.7558,
          "longitude": 37.6176,
          "height": 100
        },
        "user": {
          "email": "user@example.com",
          "phone": "+79991234567",
          "fam": "Иванов",
          "name": "Петр",
          "otc": "Сергеевич"
        },
        "level": {
          "winter": "1A",
          "summer": "1B",
          "autumn": "2A",
          "spring": "2B"
        },
        "images": []
      }
    }
    ```

3. Поиск перевалов по email пользователя

    Endpoint: GET /pereval/submitData/?user__email=<email>

    Пример ответа:

    ``` json
    {
      "status": 200,
      "message": "Найдено 2 перевала",
      "data": [
        {
          "id": 123,
          "beauty_title": "пер. Корженевского",
          "title": "Перевал Корженевского",
          "other_titles": "пер. Корж.",
          "connect": "Соединяет ледники Корженевского и Москвина",
          "add_time": "2023-09-22T13:18:13",
          "status": "new",
          "coords": {
            "latitude": 55.7558,
            "longitude": 37.6176,
            "height": 100
          },
          "user": {
            "email": "user@example.com",
            "phone": "+79991234567",
            "fam": "Иванов",
            "name": "Петр",
            "otc": "Сергеевич"
          },
          "level": {
            "winter": "1A",
            "summer": "1B",
            "autumn": "2A",
            "spring": "2B"
          },
          "images": []
        }
      ]
    } 
    ```

4. Обновление данных о перевале

    Endpoint: PATCH /pereval/submitData/<int:pass_id>

    Пример запроса:

    ``` json
    {
      "beauty_title": "пер. Корженевского (обновленный)",
      "level": {
        "winter": "2A"
      }
    }
    ```

    Пример ответа:

    ``` json
    {
      "state": 1,
      "message": "Данные перевала успешно обновлены"
    }
    ```
5. Проверка состояния сервиса

    Endpoint: GET /health

    Пример ответа:

    ``` json
    {
      "status": "OK",
      "database": "connected"
    }
    ```

## Структура базы данных

 1. Таблица users - информация о пользователях

| Поле   | Тип        | Описание       |
|--------|------------|----------------|
| id     | SERIAL     | Первичный ключ |
| email  | VARCHAR    | Email          |
| phone  | VARCHAR    | Телефон        |
| fam    | VARCHAR    | Фамилия        |
| name   | VARCHAR    | Имя            |
| otc    | VARCHAR    | Отчество       |

2. Таблица pereval_added - информация о перевалах

| Поле         | Тип        | Описание                  |
|--------------|------------|---------------------------|
| id           | SERIAL     | Первичный ключ            |
| beauty_title | VARCHAR    | Красивое название         |
| title        | VARCHAR    | Название перевала         |
| other_titles | VARCHAR    | Другие названия           |
| connect      | VARCHAR    | Соединение                |
| add_time     | TIMESTAMP  | Время добавления          |
| user_id      | INTEGER    | Внешний ключ на users     |
| latitude     | FLOAT      | Широта                    |
| longitude    | FLOAT      | Долгота                   |
| height       | INTEGER    | Высота                    |
| winter       | VARCHAR    | Уровень сложности (зима)  |
| summer       | VARCHAR    | Уровень сложности (лето)  |
| autumn       | VARCHAR    | Уровень сложности (осень) |
| spring       | VARCHAR    | Уровень сложности (весна) |
| status       | VARCHAR    | Статус модерации          |

3.Таблица pereval_images - изображения перевалов

| Поле       | Тип        | Описание                      |
|------------|------------|-------------------------------|
| id         | SERIAL     | Первичный ключ                |
| pereval_id | INTEGER    | Внешний ключ на pereval_added |
| date_added | TIMESTAMP  | Дата добавления               |
| img        | BYTEA      | Данные изображения            |
| title      | VARCHAR    | Название изображения          |

## Логирование

Логи приложения сохраняются в файл logs/app.log
содержат:

- Время запроса
- Тип запроса
- Конечную точку
- Параметры запроса
- Результат выполнения
- Ошибки (если есть)

## Ограничения

1. Обновлять можно только перевалы со статусом "new"

2. Максимальный размер JSON-запроса - 1MB

3. Все обязательные поля должны быть заполнены

## Контакты

По вопросам работы API обращайтесь: [qFILINp] <bot_bot_1901@bk.ru>