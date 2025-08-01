from flask import Flask, request, jsonify
from database import Database
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

app = Flask(__name__)


def setup_logging():
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


setup_logging()
db = Database()


@app.route('/submitData', methods=['POST'])
def submit_data():
    try:
        app.logger.info(f"Incoming request at {datetime.now(timezone.utc)}")

        if not db.is_connected():
            db.connect()
            if not db.is_connected():
                app.logger.error("Database connection failed")
                return jsonify({
                    'status': 500,
                    'message': 'Ошибка подключения к базе данных',
                    'id': None
                }), 500

        if not request.is_json:
            app.logger.warning("Request without JSON content")
            return jsonify({
                'status': 400,
                'message': 'Запрос должен содержать JSON',
                'id': None
            }), 400

        try:
            data = request.get_json()
        except Exception as e:
            app.logger.error(f"JSON decode error: {str(e)}")
            return jsonify({
                'status': 400,
                'message': 'Неверный формат JSON данных',
                'id': None
            }), 400

        if not data:
            app.logger.warning("Empty JSON data received")
            return jsonify({
                'status': 400,
                'message': 'Отсутствуют данные в запросе',
                'id': None
            }), 400

        result = db.add_pereval(data)
        app.logger.info(f"Database operation result: {result}")

        response = jsonify({
            'status': result['status'],
            'message': result['message'],
            'id': result.get('id')
        })

        if result['status'] == 200:
            app.logger.info(f"Successfully added pereval with ID {result['id']}")
        else:
            app.logger.warning(f"Validation failed: {result['message']}")

        return response, result['status']

    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 500,
            'message': f'Внутренняя ошибка сервера: {str(e)}',
            'id': None
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    try:
        if db.is_connected() or db.connect():
            return jsonify({
                'status': 'OK',
                'database': 'connected'
            }), 200
        else:
            return jsonify({
                'status': 'Degraded',
                'database': 'disconnected'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'Error',
            'error': str(e)
        }), 500


@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        db.close()
        app.logger.info("Database connection closed")
    except Exception as e:
        app.logger.error(f"Error closing database connection: {str(e)}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)