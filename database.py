import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any
from dotenv import load_dotenv
from datetime import datetime


class Database:
    def __init__(self):
        load_dotenv()
        self.db_host = os.getenv('FSTR_DB_HOST', 'localhost')
        self.db_port = int(os.getenv('FSTR_DB_PORT', 5432))
        self.db_login = os.getenv('FSTR_DB_LOGIN', 'postgres')
        self.db_pass = os.getenv('FSTR_DB_PASS', 'postgres')
        self.db_name = os.getenv('FSTR_DB_NAME', 'pereval')
        self.conn = None
        self.connect()

    def connect(self):
        try:
            if self.is_connected():
                return True

            conn_string = f"""
                host={self.db_host}
                port={self.db_port}
                dbname={self.db_name}
                user={self.db_login}
                password={self.db_pass}
                connect_timeout=3
            """
            self.conn = psycopg2.connect(conn_string.strip())
            self.conn.autocommit = False
            return True
        except psycopg2.OperationalError as e:
            print(f"Ошибка подключения к PostgreSQL: {str(e)}")
            return False

    def is_connected(self):
        return self.conn is not None and not self.conn.closed

    def close(self):
        if self.is_connected():
            self.conn.close()

    def _validate_phone(self, phone: str) -> bool:
        return bool(re.match(r'^\+[0-9]{1,3}[0-9]{6,14}$', phone))

    def _validate_email(self, email: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

    def _validate_date(self, date_str: str) -> bool:
        try:
            datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False

    def add_pereval(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {'status': 400, 'message': '', 'id': None}
        errors = []

        required_fields = ['beauty_title', 'title', 'add_time', 'user', 'coords', 'level']
        for field in required_fields:
            if field not in data:
                errors.append(f'Отсутствует обязательное поле: {field}')

        if 'user' in data:
            user = data['user']
            user_required = ['email', 'fam', 'name', 'phone']
            for field in user_required:
                if field not in user:
                    errors.append(f'Отсутствует поле пользователя: {field}')

            if 'email' in user and not self._validate_email(user['email']):
                errors.append('Неверный формат email')

            if 'phone' in user and not self._validate_phone(user['phone']):
                errors.append('Телефон должен быть в формате +<код страны><номер>')

        if 'add_time' in data and not self._validate_date(data['add_time']):
            errors.append('Неверный формат даты. Используйте YYYY-MM-DD HH:MM:SS')

        if errors:
            result['message'] = '; '.join(errors)
            return result

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Добавление пользователя
                user = data['user']
                cursor.execute(
                    """
                    INSERT INTO users (email, phone, fam, name, otc)
                    VALUES (%(email)s, %(phone)s, %(fam)s, %(name)s, %(otc)s)
                    ON CONFLICT (email) DO UPDATE
                    SET phone = EXCLUDED.phone, fam = EXCLUDED.fam, 
                        name = EXCLUDED.name, otc = EXCLUDED.otc
                    RETURNING id
                    """,
                    {
                        'email': user['email'],
                        'phone': user['phone'],
                        'fam': user['fam'],
                        'name': user['name'],
                        'otc': user.get('otc', '')
                    }
                )
                user_id = cursor.fetchone()['id']

                # Добавление перевала
                cursor.execute(
                    """
                    INSERT INTO pereval_added (
                        beauty_title, title, other_titles, connect, add_time, user_id,
                        latitude, longitude, height, winter, summer, autumn, spring
                    )
                    VALUES (
                        %(beauty_title)s, %(title)s, %(other_titles)s, %(connect)s, %(add_time)s, %(user_id)s,
                        %(latitude)s, %(longitude)s, %(height)s, %(winter)s, %(summer)s, %(autumn)s, %(spring)s
                    )
                    RETURNING id
                    """,
                    {
                        'beauty_title': data['beauty_title'],
                        'title': data['title'],
                        'other_titles': data.get('other_titles', ''),
                        'connect': data.get('connect', ''),
                        'add_time': data['add_time'],
                        'user_id': user_id,
                        'latitude': data['coords']['latitude'],
                        'longitude': data['coords']['longitude'],
                        'height': data['coords']['height'],
                        'winter': data['level'].get('winter', ''),
                        'summer': data['level'].get('summer', ''),
                        'autumn': data['level'].get('autumn', ''),
                        'spring': data['level'].get('spring', '')
                    }
                )
                pereval_id = cursor.fetchone()['id']

                # Добавление изображений
                if 'images' in data and isinstance(data['images'], list):
                    for image in data['images']:
                        if 'data' in image and 'title' in image:
                            cursor.execute(
                                """
                                INSERT INTO pereval_images (pereval_id, img, title)
                                VALUES (%(pereval_id)s, %(img)s, %(title)s)
                                """,
                                {
                                    'pereval_id': pereval_id,
                                    'img': image['data'],
                                    'title': image['title']
                                }
                            )

                self.conn.commit()
                result['status'] = 200
                result['message'] = 'Перевал успешно добавлен'
                result['id'] = pereval_id

        except psycopg2.Error as e:
            self.conn.rollback()
            result['status'] = 500
            result['message'] = f'Ошибка базы данных: {str(e)}'
            print(f"Database error: {str(e)}")
        except Exception as e:
            self.conn.rollback()
            result['status'] = 500
            result['message'] = f'Неожиданная ошибка: {str(e)}'
            print(f"Unexpected error: {str(e)}")

        return result

    def __del__(self):
        self.close()