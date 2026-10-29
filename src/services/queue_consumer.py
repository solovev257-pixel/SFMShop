import json
import logging
import time

import pika

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    logger.info("Письмо по заказу %s отправлено пользователю %s", order_id, user_id)


def update_stock(order_id: int, items: list):
    for item in items:
        logger.info("Заказ %s: со склада списан товар %s", order_id, item)


def generate_report(order_id: int):
    logger.info("Отчёт по заказу %s готов", order_id)


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
            logger.error("Не удалось подключиться к RabbitMQ: %s", error)
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

    def handle_message(self, ch, method, properties, body):
        """Обработать сообщение, при ошибке повторить"""
        # номер попытки лежит в заголовке сообщения
        attempt = (properties.headers or {}).get("x-retry-count", 0)

        try:
            message = json.loads(body)
            self.run_task(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info("Задача выполнена: %s", message)
            return
        except Exception as error:
            logger.error("Ошибка задачи (попытка %s): %s", attempt + 1, error)

        if attempt < self.max_retries:
            attempt += 1
            time.sleep(2 ** attempt)  # учебная пауза; в проде повтор делают через DLX + TTL
            ch.basic_publish(
                exchange="",
                routing_key=self.QUEUE,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={"x-retry-count": attempt},
                ),
            )
            logger.info("Задача отправлена на повтор %s/%s", attempt, self.max_retries)
        else:
            ch.basic_publish(
                exchange="",
                routing_key=self.ERROR_QUEUE,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            logger.error("Попытки кончились, задача ушла в %s", self.ERROR_QUEUE)

        ch.basic_ack(delivery_tag=method.delivery_tag)  # старую копию убираем из очереди

    def start_consuming(self):
        """Запустить воркер"""
        if not self.connect():
            return
        self.channel.basic_consume(queue=self.QUEUE, on_message_callback=self.handle_message)
        logger.info("Жду задачи в %s...", self.QUEUE)
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.connection.close()


if __name__ == "__main__":
    start_consumer("test_queue")