import json
import logging

import pika

logger = logging.getLogger(__name__)


def send_message(queue_name: str, message: dict):
    """Отправить одно сообщение в очередь (функция урока)"""
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),  # сообщение пишется на диск
    )
    print(f"Отправлено в {queue_name}: {message}")
    connection.close()


class QueueProducer:
    """Держит одно соединение с RabbitMQ и отправляет задачи по заказам"""

    QUEUE = "order_processing"

    def __init__(self, host: str = "localhost"):
        self.host = host
        self.connection = None
        self.channel = None

    def connect(self) -> bool:
        """Открыть соединение и канал, объявить очередь"""
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.QUEUE, durable=True)
            return True
        except pika.exceptions.AMQPError as error:
            logger.error("Не удалось подключиться к RabbitMQ: %s", error)
            return False

    def send_order_task(self, order_id: int, task_type: str, data: dict) -> bool:
        """Положить задачу по заказу в очередь"""
        # подключаемся только при первой отправке, дальше используем тот же канал
        if self.channel is None and not self.connect():
            return False

        message = {"task": task_type, "order_id": order_id, **data}
        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=self.QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        except pika.exceptions.AMQPError as error:
            logger.error("Задача не отправлена: %s", error)
            return False

        logger.info("Задача в очереди: %s", message)
        return True

    def close(self):
        """Закрыть соединение"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()


if __name__ == "__main__":
    send_message("test_queue", {"test": "message"})