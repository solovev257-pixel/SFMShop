import asyncio
import time


async def validate_order(order_id: int) -> dict:
    """Валидация заказа"""

    await asyncio.sleep(1)
    return {"order_id": order_id, "valid": True}


async def reserve_items(order_id: int) -> dict:
    """Резервирование товаров"""
    await asyncio.sleep(1.5)
    return {"order_id": order_id, "reserved": True}


async def verify_address(order_id: int) -> dict:
    """Проверка адреса доставки"""
    await asyncio.sleep(0.5)
    return {"order_id": order_id, "address_valid": True}


def build_error_result(order_id: int, status: str, error_group: ExceptionGroup) -> dict:
    """Собирает ответ с ошибками, если обработка заказа не удалась"""
    messages = [str(error) for error in error_group.exceptions]
    return {"order_id": order_id, "status": status, "errors": messages}


async def process_order_tg(order_id: int) -> dict:
    """Три проверки заказа одновременно: если одна падает, остальные отменяются"""
    try:
        # Все задачи стартуют сразу, из блока выходим только когда закончатся все три
        async with asyncio.TaskGroup() as tg:
            validation_task = tg.create_task(validate_order(order_id), name="validation")
            reservation_task = tg.create_task(reserve_items(order_id), name="reservation")
            address_task = tg.create_task(verify_address(order_id), name="address")

    except* ValueError as error_group:
        # Заказ не прошёл проверку данных
        result = build_error_result(order_id, "validation_error", error_group)

    except* ConnectionError as error_group:
        # Один из сервисов не ответил
        result = build_error_result(order_id, "service_error", error_group)

    else:
        # Ошибок не было: забираем результаты уже после выхода из группы
        result = {
            "order_id": order_id,
            "status": "ready",
            "validation": validation_task.result(),
            "reservation": reservation_task.result(),
            "address": address_task.result(),
        }

    return result


async def main():
    started_at = time.time()
    order_result = await process_order_tg(101)
    elapsed = time.time() - started_at

    print(f"Результат: {order_result}")
    print(f"Время обработки: {elapsed:.2f} секунд")


if __name__ == "__main__":
    asyncio.run(main())