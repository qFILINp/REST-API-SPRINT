"""
Главное Flask-приложение для API перевалов с Swagger-документацией.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import Flask, request
from flask_restx import Api, Resource, fields, Namespace
from database import Database


def create_app() -> Flask:
    """Создает и настраивает Flask-приложение.

    Возвращает:
        Flask: Настроенное приложение Flask.
    """
    app = Flask(__name__)
    _setup_logging(app)
    db = Database()

    # Инициализация Swagger
    api = Api(
        app,
        version='1.0',
        title='API для перевалов',
        description='API для управления данными о горных перевалах',
        doc='/swagger/',
        default='Перевалы',
        default_label='Операции с перевалами',
        contact='bot_bot_1901@bk.ru',

    )

    # Модели данных для Swagger
    user_model = api.model('Пользователь', {
        'email': fields.String(required=True, description='Email пользователя', example='user@example.com'),
        'fam': fields.String(required=True, description='Фамилия', example='Иванов'),
        'name': fields.String(required=True, description='Имя', example='Иван'),
        'otc': fields.String(description='Отчество', example='Иванович'),
        'phone': fields.String(required=True, description='Телефон', example='+79001234567')
    })

    coords_model = api.model('Координаты', {
        'latitude': fields.Float(required=True, description='Широта', example=45.1234),
        'longitude': fields.Float(required=True, description='Долгота', example=90.5678),
        'height': fields.Integer(required=True, description='Высота', example=1500)
    })

    level_model = api.model('Уровень сложности', {
        'winter': fields.String(description='Зимний уровень сложности', example='1A'),
        'summer': fields.String(description='Летний уровень сложности', example='1B'),
        'autumn': fields.String(description='Осенний уровень сложности', example='2A'),
        'spring': fields.String(description='Весенний уровень сложности', example='2B')
    })

    pereval_model = api.model('Перевал', {
        'beauty_title': fields.String(required=True, description='Красивое название', example='Красивый перевал'),
        'title': fields.String(required=True, description='Название перевала', example='Перевал Славы'),
        'other_titles': fields.String(description='Другие названия', example='Перевал Победы'),
        'connect': fields.String(description='Соединение', example='Соединяет долины рек'),
        'add_time': fields.DateTime(required=True, description='Время добавления', example='2023-01-01T12:00:00Z'),
        'user': fields.Nested(user_model, required=True, description='Данные пользователя'),
        'coords': fields.Nested(coords_model, required=True, description='Координаты'),
        'level': fields.Nested(level_model, description='Уровни сложности')
    })

    pereval_response_model = api.model('Ответ о перевале', {
        'status': fields.Integer(description='Код статуса', example=200),
        'message': fields.String(description='Сообщение', example='Успешно'),
        'id': fields.Integer(description='ID созданной записи', example=1)
    })

    error_model = api.model('Ошибка', {
        'status': fields.Integer(description='Код ошибки', example=400),
        'message': fields.String(description='Описание ошибки', example='Неверные данные'),
        'data': fields.Raw(description='Дополнительные данные')
    })

    # Пространство имен для операций с перевалами
    pereval_ns = Namespace('pereval', description='Операции с перевалами')
    api.add_namespace(pereval_ns)

    @pereval_ns.route('/submitData')
    class PerevalSubmit(Resource):
        @pereval_ns.expect(pereval_model)
        @pereval_ns.response(200, 'Успешно', pereval_response_model)
        @pereval_ns.response(400, 'Некорректные данные', error_model)
        @pereval_ns.response(500, 'Ошибка сервера', error_model)
        def post(self) -> tuple:
            """Добавляет новые данные о перевале."""
            try:
                _log_request(app, 'submit_data')

                if not _check_db_connection(app, db):
                    return {'status': 500, 'message': 'Ошибка подключения к базе данных'}, 500

                data = request.get_json()
                if not data:
                    app.logger.warning("Получены пустые JSON-данные")
                    return {'status': 400, 'message': 'Некорректные JSON-данные'}, 400

                # Валидация обязательных полей
                validation_errors = _validate_pereval_data(data)
                if validation_errors:
                    app.logger.warning(f"Ошибки валидации: {validation_errors}")
                    return {
                        'status': 400,
                        'message': 'Не заполнены обязательные поля',
                        'data': validation_errors
                    }, 400

                result = db.add_pereval(data)
                _log_result(app, 'submit_data', result)

                return {
                    'status': result['status'],
                    'message': result['message'],
                    'id': result.get('id')
                }, result['status']

            except Exception as e:
                app.logger.error(f"Непредвиденная ошибка: {str(e)}", exc_info=True)
                return {'status': 500, 'message': f'Внутренняя ошибка сервера: {str(e)}'}, 500

    @pereval_ns.route('/submitData/<int:pass_id>')
    @pereval_ns.param('pass_id', 'ID перевала')
    class PerevalDetail(Resource):
        @pereval_ns.response(200, 'Успешно')
        @pereval_ns.response(404, 'Перевал не найден', error_model)
        @pereval_ns.response(500, 'Ошибка сервера', error_model)
        def get(self, pass_id: int) -> tuple:
            """Получает данные о перевале по его ID."""
            try:
                app.logger.info(f"Получение перевала ID {pass_id} в {datetime.now(timezone.utc)}")

                if not _check_db_connection(app, db):
                    return {'status': 500, 'message': 'Ошибка подключения к базе данных'}, 500

                result = db.get_pereval_by_id(pass_id)
                _log_result(app, 'get_pereval', result)

                if result['status'] == 200:
                    return {
                        'status': 200,
                        'message': 'Данные успешно получены',
                        'data': result['data']
                    }, 200
                return {
                    'status': result['status'],
                    'message': result['message'],
                    'data': None
                }, result['status']

            except Exception as e:
                app.logger.error(f"Ошибка при получении перевала {pass_id}: {str(e)}", exc_info=True)
                return {'status': 500, 'message': f'Внутренняя ошибка сервера: {str(e)}'}, 500

        @pereval_ns.expect(pereval_model)
        @pereval_ns.response(200, 'Успешно')
        @pereval_ns.response(400, 'Некорректные данные', error_model)
        @pereval_ns.response(404, 'Перевал не найден', error_model)
        @pereval_ns.response(500, 'Ошибка сервера', error_model)
        def patch(self, pass_id: int) -> tuple:
            """Обновляет данные о перевале."""
            try:
                app.logger.info(f"Запрос на обновление перевала ID {pass_id} в {datetime.now(timezone.utc)}")

                if not _check_db_connection(app, db):
                    return {'status': 500, 'message': 'Ошибка подключения к базе данных'}, 500

                update_data = request.get_json()
                if not update_data:
                    app.logger.warning("Получены пустые JSON-данные")
                    return {'status': 400, 'message': 'Некорректные JSON-данные'}, 400

                result = db.update_pereval(pass_id, update_data)
                _log_result(app, 'update_pereval', result)

                return {
                    'state': result['state'],
                    'message': result['message']
                }, 200 if result['state'] == 1 else 400

            except Exception as e:
                app.logger.error(f"Ошибка при обновлении: {str(e)}", exc_info=True)
                return {'status': 500, 'message': f'Внутренняя ошибка сервера: {str(e)}'}, 500

    @pereval_ns.route('/submitData/')
    class PerevalByEmail(Resource):
        @pereval_ns.param('user__email', 'Email пользователя', required=True)
        @pereval_ns.response(200, 'Успешно')
        @pereval_ns.response(400, 'Не указан email', error_model)
        @pereval_ns.response(500, 'Ошибка сервера', error_model)
        def get(self) -> tuple:
            """Получает перевалы по email пользователя."""
            try:
                email = request.args.get('user__email')
                if not email:
                    app.logger.warning("Не указан email пользователя")
                    return {'status': 400, 'message': 'Необходимо указать email пользователя'}, 400

                app.logger.info(f"Поиск перевалов для email: {email}")

                if not _check_db_connection(app, db):
                    return {'status': 500, 'message': 'Ошибка подключения к базе данных'}, 500

                result = db.get_pereval_by_email(email)
                app.logger.info(f"Найдено {len(result['data'])} перевалов")

                return {
                    'status': result['status'],
                    'message': result['message'],
                    'data': result['data']
                }, result['status']

            except Exception as e:
                app.logger.error(f"Ошибка при поиске по email: {str(e)}")
                return {'status': 500, 'message': f'Внутренняя ошибка сервера: {str(e)}'}, 500

    # Эндпоинт для проверки состояния
    @api.route('/health')
    class HealthCheck(Resource):
        @api.response(200, 'Сервис работает')
        @api.response(500, 'Проблемы с сервисом')
        def get(self) -> tuple:
            """Проверяет состояние приложения и базы данных."""
            try:
                if db.is_connected() or db.connect():
                    return {
                        'status': 'OK',
                        'database': 'connected'
                    }, 200
                return {
                    'status': 'Degraded',
                    'database': 'disconnected'
                }, 500
            except Exception as e:
                return {
                    'status': 'Error',
                    'error': str(e)
                }, 500

    @app.teardown_appcontext
    def shutdown_session(exception: Optional[Exception] = None) -> None:
        """Закрывает соединение с базой данных при завершении работы приложения."""
        try:
            db.close()
            app.logger.info("Соединение с базой данных закрыто")
        except Exception as e:
            app.logger.error(f"Ошибка при закрытии соединения с БД: {str(e)}")

    return app


def _validate_pereval_data(data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Проверяет данные перевала перед добавлением.

    Аргументы:
        data: Данные перевала для проверки.

    Возвращает:
        Словарь с ошибками или None если ошибок нет.
    """
    errors = {}

    # Проверка обязательных полей перевала
    if not data.get('beauty_title') or data.get('beauty_title') == "":
        errors['beauty_title'] = 'Поле обязательно для заполнения'
    if not data.get('title') or data.get('title') == "":
        errors['title'] = 'Поле обязательно для заполнения'
    if not data.get('add_time'):
        errors['add_time'] = 'Поле обязательно для заполнения'

    # Проверка координат
    if 'coords' not in data:
        errors['coords'] = 'Координаты обязательны'
    else:
        coords = data['coords']
        if not coords.get('latitude') and coords.get('latitude') != 0:
            errors['coords.latitude'] = 'Поле обязательно для заполнения'
        if not coords.get('longitude') and coords.get('longitude') != 0:
            errors['coords.longitude'] = 'Поле обязательно для заполнения'
        if not coords.get('height') and coords.get('height') != 0:
            errors['coords.height'] = 'Поле обязательно для заполнения'

    # Проверка пользователя
    if 'user' not in data:
        errors['user'] = 'Данные пользователя обязательны'
    else:
        user = data['user']
        if not user.get('email') or user.get('email') == "":
            errors['user.email'] = 'Поле обязательно для заполнения'
        if not user.get('phone') or user.get('phone') == "":
            errors['user.phone'] = 'Поле обязательно для заполнения'
        if not user.get('fam') or user.get('fam') == "":
            errors['user.fam'] = 'Поле обязательно для заполнения'
        if not user.get('name') or user.get('name') == "":
            errors['user.name'] = 'Поле обязательно для заполнения'

    return errors if errors else None


def _setup_logging(app: Flask) -> None:
    """Настраивает логирование для приложения.

    Аргументы:
        app: Экземпляр Flask-приложения.
    """
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = RotatingFileHandler(
        f'{log_dir}/app.log',
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _check_db_connection(app: Flask, db: Database) -> bool:
    """Проверяет соединение с базой данных.

    Аргументы:
        app: Экземпляр Flask-приложения.
        db: Экземпляр класса Database.

    Возвращает:
        bool: True если соединение установлено, False в противном случае.
    """
    if not db.is_connected():
        db.connect()
        if not db.is_connected():
            app.logger.error("Не удалось подключиться к базе данных")
            return False
    return True


def _log_request(app: Flask, endpoint: str) -> None:
    """Логирует информацию о входящем запросе.

    Аргументы:
        app: Экземпляр Flask-приложения.
        endpoint: Название конечной точки API.
    """
    app.logger.info(f"Входящий запрос к {endpoint} в {datetime.now(timezone.utc)}")


def _log_result(app: Flask, endpoint: str, result: Dict[str, Any]) -> None:
    """Логирует результат выполнения операции.

    Аргументы:
        app: Экземпляр Flask-приложения.
        endpoint: Название конечной точки API.
        result: Результат выполнения операции.
    """
    if result.get('status', 500) == 200 or result.get('state', 0) == 1:
        app.logger.info(f"{endpoint} успешно: {result}")
    else:
        app.logger.warning(f"{endpoint} ошибка: {result}")


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)