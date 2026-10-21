"""Шесть сценариев помощника поддержки без ключа VseGPT: модель заменена заглушкой."""
import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace

from openai import APIConnectionError

from src.services.support_service import answer_support


@dataclass
class DemoOrder:
    id: int
    user_id: int
    status: str


class DemoOrderRepository:
    async def get_by_id(self, order_id: int):
        orders = {
            101: DemoOrder(id=101, user_id=1, status="created"),
            202: DemoOrder(id=202, user_id=2, status="paid"),
        }
        return orders.get(order_id)


def llm_response(payload: dict):
    """Ответ в том же виде, что у openai: choices[0].message.content и usage"""
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)))],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=20),
    )


class FakeLLM:
    """Заглушка модели: по очереди отдаёт заранее заготовленные ответы"""

    def __init__(self, answers: list[dict], fail: bool = False):
        self.answers = list(answers)
        self.fail = fail
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        if self.fail:
            raise APIConnectionError(request=None)
        return llm_response(self.answers.pop(0))


SCENARIOS = [
    (
        "Вопрос о доставке",
        "Сколько занимает доставка по городу?",
        [
            {"action": "knowledge", "topic": "delivery", "order_id": None},
            {"answer": "Доставка по городу занимает 2–3 рабочих дня.", "sources": ["delivery-1"], "insufficient_data": False},
        ],
        False,
        "ответ из delivery-1, handoff=False",
    ),
    (
        "Неизвестная цена доставки",
        "Есть ли бесплатная доставка в другой город?",
        [
            {"action": "knowledge", "topic": "delivery", "order_id": None},
            {"answer": "Нет данных", "sources": [], "insufficient_data": True},
        ],
        False,
        "к оператору, sources пуст",
    ),
    (
        "Свой заказ",
        "Где мой заказ 101?",
        [{"action": "order", "topic": "unknown", "order_id": 101}],
        False,
        "статус заказа 101",
    ),
    (
        "Чужой заказ",
        "Где заказ 202?",
        [{"action": "order", "topic": "unknown", "order_id": 202}],
        False,
        "«Заказ не найден или недоступен»",
    ),
    (
        "Несуществующий заказ",
        "Где заказ 999?",
        [{"action": "order", "topic": "unknown", "order_id": 999}],
        False,
        "тот же текст, что для чужого",
    ),
    (
        "API модели недоступен",
        "Сколько занимает доставка?",
        [],
        True,
        "к оператору, handoff=True",
    ),
]


async def main():
    repo = DemoOrderRepository()
    for title, question, answers, fail, expected in SCENARIOS:
        result = await answer_support(
            question=question,
            current_user_id=1,
            order_repo=repo,
            client=FakeLLM(answers, fail=fail),
        )
        print(f"[{title}] ожидали: {expected}")
        print(f"    получили: answer={result.answer!r} sources={result.sources} handoff={result.handoff}")
    print("[Запрос без токена] проверяется в Swagger: POST /api/v1/support без Authorization -> 401")


if __name__ == "__main__":
    asyncio.run(main())