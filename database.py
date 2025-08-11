"""
Слой взаимодействия с базой данных для API перевалов.
Обрабатывает все операции с PostgreSQL.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

load_dotenv()


class Database:
    """Класс для управления подключением и операциями с базой данных."""

    def __init__(self):
        """Инициализирует соединение с базой данных (пока не устанавливает его)."""
        self.conn = None

    def connect(self) -> bool:
        """Устанавливает соединение с базой данных.

        Возвращает:
            bool: True если подключение успешно, False в случае ошибки.
        """
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('FSTR_DB_HOST'),
                port=os.getenv('FSTR_DB_PORT'),
                database=os.getenv('FSTR_DB_NAME'),
                user=os.getenv('FSTR_DB_LOGIN'),
                password=os.getenv('FSTR_DB_PASS'),
                connect_timeout=5
            )
            return True
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return False

    def is_connected(self) -> bool:
        """Проверяет, активно ли соединение с базой данных.

        Возвращает:
            bool: True если соединение активно, False в противном случае.
        """
        return self.conn is not None and not self.conn.closed

    def close(self) -> None:
        """Закрывает соединение с базой данных, если оно активно."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def add_pereval(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Добавляет новый перевал в базу данных.

        Аргументы:
            data: Словарь с данными о перевале.

        Возвращает:
            Словарь со статусом операции и ID созданной записи.
        """
        try:
            if not self.is_connected():
                return self._error_response(500, 'Нет соединения с базой данных')

            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Проверка обязательных полей
                if not self._validate_pereval_data(data):
                    return self._error_response(400, 'Не заполнены обязательные поля')

                user_id = self._get_or_create_user(cursor, data['user'])
                pereval_id = self._insert_pereval(cursor, data, user_id)
                self.conn.commit()

                return {
                    'status': 200,
                    'message': 'Перевал успешно добавлен',
                    'id': pereval_id
                }

        except Exception as e:
            self._rollback()
            return self._error_response(500, f'Ошибка базы данных: {str(e)}')

    def get_pereval_by_id(self, pass_id: int) -> Dict[str, Any]:
        """Получает данные о перевале по его ID.

        Аргументы:
            pass_id: ID перевала для поиска.

        Возвращает:
            Словарь с данными о перевале или сообщением об ошибке.
        """
        try:
            if not self.is_connected():
                return self._error_response(500, 'Нет соединения с базой данных', None)

            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                pereval = self._fetch_pereval(cursor, pass_id)
                if not pereval:
                    return self._error_response(404, 'Перевал не найден', None)

                images = self._fetch_pereval_images(cursor, pass_id)
                data = self._format_pereval_data(pereval, images)

                return {
                    'status': 200,
                    'message': 'Данные успешно получены',
                    'data': data
                }

        except Exception as e:
            return self._error_response(500, f'Ошибка базы данных: {str(e)}', None)

    def get_pereval_by_email(self, email: str) -> Dict[str, Any]:
        """Получает все перевалы, добавленные пользователем с указанным email.

        Аргументы:
            email: Email пользователя для поиска.

        Возвращает:
            Словарь со списком перевалов или сообщением об ошибке.
        """
        try:
            if not self.is_connected():
                return self._error_response(500, 'Нет соединения с базой данных', [])

            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                user_id = self._get_user_id_by_email(cursor, email)
                if not user_id:
                    return self._error_response(404, 'Пользователь не найден', [])

                perevals = self._fetch_user_pereval(cursor, email)
                result = [
                    self._format_pereval_data(p, self._fetch_pereval_images(cursor, p['id']))
                    for p in perevals
                ]

                return {
                    'status': 200,
                    'message': f'Найдено {len(result)} перевалов',
                    'data': result
                }

        except Exception as e:
            return self._error_response(500, f'Ошибка базы данных: {str(e)}', [])

    def update_pereval(self, pass_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет данные о перевале.

        Аргументы:
            pass_id: ID перевала для обновления.
            update_data: Словарь с полями для обновления.

        Возвращает:
            Словарь с результатом операции.
        """
        try:
            if not self.is_connected():
                return self._operation_failed('Нет соединения с базой данных')

            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                pereval = self._fetch_pereval_for_update(cursor, pass_id)
                if not pereval:
                    return self._operation_failed('Перевал не найден')

                if not self._validate_update(cursor, pereval, update_data):
                    return self._operation_failed('Обновление невозможно: неверные данные или статус')

                update_fields, update_values = self._prepare_update(update_data)
                if not update_fields:
                    return self._operation_failed('Нет данных для обновления')

                self._execute_update(cursor, pass_id, update_fields, update_values)
                self.conn.commit()

                return self._operation_success('Данные перевала успешно обновлены')

        except Exception as e:
            self._rollback()
            return self._operation_failed(f'Ошибка базы данных: {str(e)}')

    # Вспомогательные методы
    def _validate_pereval_data(self, data: Dict[str, Any]) -> bool:
        """Проверяет наличие всех обязательных полей в данных о перевале."""
        required_fields = [
            data.get('beauty_title'),
            data.get('title'),
            data.get('add_time'),
            data.get('coords', {}).get('latitude') is not None,
            data.get('coords', {}).get('longitude') is not None,
            data.get('coords', {}).get('height') is not None,
            data.get('user', {}).get('email'),
            data.get('user', {}).get('phone'),
            data.get('user', {}).get('fam'),
            data.get('user', {}).get('name')
        ]
        return all(required_fields)

    def _get_or_create_user(self, cursor, user_data: Dict[str, Any]) -> int:
        """Находит существующего пользователя или создает нового."""
        cursor.execute(
            "SELECT id FROM users WHERE email = %s OR phone = %s",
            (user_data['email'], user_data['phone'])
        )
        user = cursor.fetchone()

        if not user:
            cursor.execute(
                """INSERT INTO users (email, phone, fam, name, otc)
                VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (
                    user_data['email'],
                    user_data['phone'],
                    user_data['fam'],
                    user_data['name'],
                    user_data.get('otc', '')
                )
            )
            return cursor.fetchone()['id']
        return user['id']

    def _insert_pereval(self, cursor, data: Dict[str, Any], user_id: int) -> int:
        """Добавляет новую запись о перевале в базу данных."""
        cursor.execute(
            """INSERT INTO pereval_added (
                beauty_title, title, other_titles, connect, add_time,
                user_id, latitude, longitude, height,
                winter, summer, autumn, spring
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id""",
            (
                data['beauty_title'],
                data['title'],
                data.get('other_titles'),
                data.get('connect'),
                data['add_time'],
                user_id,
                data['coords']['latitude'],
                data['coords']['longitude'],
                data['coords']['height'],
                data.get('level', {}).get('winter'),
                data.get('level', {}).get('summer'),
                data.get('level', {}).get('autumn'),
                data.get('level', {}).get('spring')
            )
        )
        return cursor.fetchone()['id']

    def _fetch_pereval(self, cursor, pass_id: int) -> Optional[Dict[str, Any]]:
        """Получает данные о перевале по его ID."""
        cursor.execute("""
            SELECT p.*, u.email, u.phone, u.fam, u.name, u.otc
            FROM pereval_added p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = %s
        """, (pass_id,))
        return cursor.fetchone()

    def _fetch_pereval_images(self, cursor, pass_id: int) -> List[Dict[str, Any]]:
        """Получает все изображения для указанного перевала."""
        cursor.execute("""
            SELECT id, title, img
            FROM pereval_images
            WHERE pereval_id = %s
        """, (pass_id,))
        return cursor.fetchall()

    def _format_pereval_data(self, pereval: Dict[str, Any], images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Форматирует данные о перевале для ответа API."""
        return {
            'id': pereval['id'],
            'beauty_title': pereval['beauty_title'],
            'title': pereval['title'],
            'other_titles': pereval['other_titles'],
            'connect': pereval['connect'],
            'add_time': pereval['add_time'].isoformat() if pereval['add_time'] else None,
            'status': pereval['status'],
            'coords': {
                'latitude': float(pereval['latitude']),
                'longitude': float(pereval['longitude']),
                'height': pereval['height']
            },
            'user': {
                'email': pereval['email'],
                'phone': pereval['phone'],
                'fam': pereval['fam'],
                'name': pereval['name'],
                'otc': pereval['otc']
            },
            'level': {
                'winter': pereval['winter'],
                'summer': pereval['summer'],
                'autumn': pereval['autumn'],
                'spring': pereval['spring']
            },
            'images': [{
                'id': img['id'],
                'title': img['title'],
                'data': img['img'].tobytes().hex() if img['img'] else None
            } for img in images]
        }

    def _get_user_id_by_email(self, cursor, email: str) -> Optional[int]:
        """Находит ID пользователя по его email."""
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        return user['id'] if user else None

    def _fetch_user_pereval(self, cursor, email: str) -> List[Dict[str, Any]]:
        """Получает все перевалы, добавленные пользователем с указанным email."""
        cursor.execute("""
            SELECT p.*, u.email, u.phone, u.fam, u.name, u.otc
            FROM pereval_added p
            JOIN users u ON p.user_id = u.id
            WHERE u.email = %s
            ORDER BY p.date_added DESC
        """, (email,))
        return cursor.fetchall()

    def _fetch_pereval_for_update(self, cursor, pass_id: int) -> Optional[Dict[str, Any]]:
        """Получает перевал для проверки перед обновлением."""
        cursor.execute(
            "SELECT status, user_id FROM pereval_added WHERE id = %s",
            (pass_id,)
        )
        return cursor.fetchone()

    def _validate_update(self, cursor, pereval: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        """Проверяет возможность обновления данных перевала."""
        if pereval['status'] != 'new':
            return False

        if 'user' in update_data:
            user_data = update_data['user']
            cursor.execute(
                "SELECT id FROM users WHERE id = %s AND email = %s AND phone = %s AND fam = %s AND name = %s AND otc = %s",
                (
                    pereval['user_id'],
                    user_data.get('email'),
                    user_data.get('phone'),
                    user_data.get('fam'),
                    user_data.get('name'),
                    user_data.get('otc')
                )
            )
            if not cursor.fetchone():
                return False
        return True

    def _prepare_update(self, update_data: Dict[str, Any]) -> tuple:
        """Подготавливает поля и значения для обновления."""
        update_fields = []
        update_values = []

        if 'coords' in update_data:
            coords = update_data['coords']
            if 'latitude' in coords:
                update_fields.append("latitude = %s")
                update_values.append(coords['latitude'])
            if 'longitude' in coords:
                update_fields.append("longitude = %s")
                update_values.append(coords['longitude'])
            if 'height' in coords:
                update_fields.append("height = %s")
                update_values.append(coords['height'])

        if 'level' in update_data:
            level = update_data['level']
            for season in ['winter', 'summer', 'autumn', 'spring']:
                if season in level:
                    update_fields.append(f"{season} = %s")
                    update_values.append(level[season])

        for field in ['beauty_title', 'title', 'other_titles', 'connect', 'add_time']:
            if field in update_data:
                update_fields.append(f"{field} = %s")
                update_values.append(update_data[field])

        return update_fields, update_values

    def _execute_update(self, cursor, pass_id: int, update_fields: List[str], update_values: List[Any]) -> None:
        """Выполняет запрос на обновление данных перевала."""
        update_values.append(pass_id)
        update_query = f"""
            UPDATE pereval_added
            SET {', '.join(update_fields)}
            WHERE id = %s
        """
        cursor.execute(update_query, update_values)

    def _rollback(self) -> None:
        """Откатывает текущую транзакцию."""
        if self.conn:
            self.conn.rollback()

    def _error_response(self, status: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Создает стандартный ответ об ошибке."""
        return {
            'status': status,
            'message': message,
            'data': data
        }

    def _operation_success(self, message: str) -> Dict[str, Any]:
        """Создает стандартный ответ об успешной операции."""
        return {
            'state': 1,
            'message': message
        }

    def _operation_failed(self, message: str) -> Dict[str, Any]:
        """Создает стандартный ответ о неудачной операции."""
        return {
            'state': 0,
            'message': message
        }