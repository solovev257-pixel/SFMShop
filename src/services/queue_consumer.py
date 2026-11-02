import json
import logging
import sys
import time

import pika

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LogService пишет в MongoDB; если Mongo/pymongo нет, воркер работает только с консольным логом
try:
    from src.services.log_service import save_log
except ImportError:
    save_log = None


def log_event(level: int, text: str, **extra):
    """Записать событие в консоль и в LogService"""
    global save_log
    logger.log(level, text)
    if save_log is None:
        return
    try:
        save_log({"type": "queue", "level": logging.getLevelName(level), "message": text, **extra})
    except Exception as error:  # падение логера не должно ронять обработку задачи
        logger.warning("LogService недоступен, дальше пишу только в консоль: %s", error)
        save_log = None  # не ждём Mongo на каждой строке


# --- функции урока ---

def process_message(ch, method, properties, body):
    """Простая обработка сообщения (функция урока)"""
    message = json.loads(body)
    print(f"Получено: {message}")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer(queue_name: str):
    """Простой consumer (функция урока)"""
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_consume(queue=queue_name, on_message_callback=process_message)
    print(f"Жду сообщения в {queue_name}...")
    channel.start_consuming()


# --- обработчики задач (учебные заглушки, пишут в лог) ---

def send_email(order_id: int, user_id: int):
    log_event(logging.INFO, f"Письмо по заказу {order_id} отправлено пользователю {user_id}", order_id=order_id)


def update_stock(order_id: int, items: list):
    for item in items:
        log_event(logging.INFO, f"Заказ {order_id}: со склада списан товар {item}", order_id=order_id)


def generate_report(order_id: int):
    log_event(logging.INFO, f"Отчёт по заказу {order_id} готов", order_id=order_id)


# --- consumer с повторами ---

class QueueConsumer:
    """Разбирает задачи по заказам: 3 повтора, потом очередь ошибок"""

    QUEUE = "order_processing"
    ERROR_QUEUE = "order_processing_errors"

    def __init__(self, host: str = "localhost", max_retries: int = 3):
        self.host = host
        self.max_retries = max_retries
        self.connection = None
        self.channel = None

    def connect(self) -> bool:
        """Подключиться и объявить обе очереди"""
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.QUEUE, durable=True)
            self.channel.queue_declare(queue=self.ERROR_QUEUE, durable=True)
            self.channel.basic_qos(prefetch_count=1)  # по одной задаче на воркер
            return True
        except pika.exceptions.AMQPError as error:
            log_event(logging.ERROR, f"Не удалось подключиться к RabbitMQ: {error}")
            return False

    def run_task(self, message: dict):
        """Вызвать нужный обработчик по типу задачи"""
        task = message.get("task")
        order_id = message.get("order_id")
        if task == "send_email":
            send_email(order_id, message["user_id"])
        elif task == "update_stock":
            update_stock(order_id, message["items"])
        elif task == "generate_report":
            generate_report(order_id)
        else:
            raise ValueError(f"Неизвестная задача: {task}")

    def process_message(self, ch, method, properties, body):
        """Обработать сообщение, при ошибке повторить"""
        # номер попытки лежит в заголовке сообщения
        attempt = (properties.headers or {}).get("x-retry-count", 0)

        try:
            message = json.loads(body)
            self.run_task(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            log_event(logging.INFO, f"Задача выполнена: {message}")
            return
        except Exception as error:
            log_event(logging.ERROR, f"Ошибка задачи (попытка {attempt + 1}): {error}")

        if attempt < self.max_retries:
            attempt += 1
            time.sleep(2 ** (attempt - 1))  # пауза 1, 2, 4 с; в проде повтор делают через DLX + TTL
            ch.basic_publish(
                exchange="",
                routing_key=self.QUEUE,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={"x-retry-count": attempt},
                ),
            )
            log_event(logging.WARNING, f"Задача отправлена на повтор {attempt}/{self.max_retries}")
        else:
            ch.basic_publish(
                exchange="",
                routing_key=self.ERROR_QUEUE,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            log_event(logging.ERROR, f"Попытки кончились, задача ушла в {self.ERROR_QUEUE}")

        ch.basic_ack(delivery_tag=method.delivery_tag)  # старую копию убираем из очереди

    def start_consuming(self):
        """Запустить воркер"""
        if not self.connect():
            return
        self.channel.basic_consume(queue=self.QUEUE, on_message_callback=self.process_message)
        log_event(logging.INFO, f"Жду задачи в {self.QUEUE}...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.connection.close()


if __name__ == "__main__":
    # python -m src.services.queue_consumer        -> воркер заказов (можно открыть несколько терминалов)
    # python -m src.services.queue_consumer test   -> простой consumer урока для test_queue
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        start_consumer("test_queue")
    else:
        QueueConsumer().start_consuming()