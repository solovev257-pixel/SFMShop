from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(
    host=os.getenv('MONGO_HOST', 'localhost'),
    port=int(os.getenv('MONGO_PORT', 27017))
)

db = client['sfmshop_logs']
logs_collection = db['logs']

def save_log(log_data):
    if 'timestamp' not in log_data:
        log_data['timestamp'] = datetime.now()
    result = logs_collection.insert_one(log_data)
    return result.inserted_id

def get_logs_by_status_code(min_status, max_status):
    logs = logs_collection.find({
        "status_code": {"$gte": min_status, "$lt": max_status}
    })
    return list(logs)

def get_logs_by_date_range(start_date, end_date):
    logs = logs_collection.find({
        "timestamp": {"$gte": start_date, "$lte": end_date}
    })
    return list(logs)

def get_logs_by_ip(ip):
    logs = logs_collection.find({"ip": ip})
    return list(logs)

def get_logs_statistics():
    type_stats = logs_collection.aggregate([
        {"$group": {"_id": "$type", "count": {"$sum": 1}}}
    ])
    status_stats = logs_collection.aggregate([
        {"$group": {"_id": "$status_code", "count": {"$sum": 1}}}
    ])
    return {
        "by_type": list(type_stats),
        "by_status": list(status_stats),
        "total": logs_collection.count_documents({})
    }

# ---------- Логирование событий приложения ----------

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class LogService:
    """Сервис логирования SFMShop: пять уровней, запись в файл и в консоль"""

    def __init__(self, log_file: str = "app.log", level: int = logging.DEBUG):
        self.logger = logging.getLogger("sfmshop")
        self.logger.setLevel(level)
        self.logger.propagate = False
        # хендлеры добавляем один раз, даже если модуль импортирован повторно
        if not self.logger.handlers:
            formatter = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
            for handler in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()):
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

    def debug(self, message: str, **kwargs):
        self.logger.debug(f"{message} | {kwargs}")

    def info(self, message: str, **kwargs):
        self.logger.info(f"{message} | {kwargs}")

    def warning(self, message: str, **kwargs):
        self.logger.warning(f"{message} | {kwargs}")

    def error(self, message: str, **kwargs):
        self.logger.error(f"{message} | {kwargs}")

    def exception(self, message: str, **kwargs):
        """Ошибка вместе с traceback, вызывать внутри except"""
        self.logger.exception(f"{message} | {kwargs}")

    def critical(self, message: str, **kwargs):
        """Критическая ошибка: пишем в лог и отправляем алерт"""
        self.logger.critical(f"АЛЕРТ: {message} | {kwargs}")
        self.send_alert(message, **kwargs)

    def send_alert(self, message: str, **kwargs):
        """Алерт: сюда подключается Telegram, почта или Slack"""
        print(f"[ALERT] {message} | {kwargs}")


# Мониторинг ошибок через Sentry (подключается в src/api/main.py при наличии DSN):
# import sentry_sdk
# sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=1.0)
# После этого необработанные ошибки FastAPI сами уходят в Sentry с traceback.

log_service = LogService()


if __name__ == "__main__":
    stats = get_logs_statistics()
    print(f"Статистика: {stats}")