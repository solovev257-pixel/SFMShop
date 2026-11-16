import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import APITimeoutError

from src.services.support_service import (
    answer_support,
    ask_json,
    DOCUMENTS,
    OPERATOR_ANSWER,
    ORDER_NOT_FOUND,
    PLAN_PROMPT,
    ANSWER_PROMPT,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def order_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    return repo


def make_response(
    data,
    input_tokens=100,
    output_tokens=20,
):
    content = (
        data if isinstance(data, str)
        else json.dumps(data, ensure_ascii=False)
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=content),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        ),
    )


def assert_operator(result):
    assert result.answer == OPERATOR_ANSWER
    assert result.handoff is True
    assert result.sources == []


# 1. Вопрос о доставке

@pytest.mark.anyio
async def test_delivery_question(mock_client, order_repo):
    mock_client.chat.completions.create.side_effect = [
        make_response({
            "action": "knowledge",
            "topic": "delivery",
        }),
        make_response({
            "answer": "Доставка занимает 2–3 рабочих дня.",
            "sources": ["delivery-1"],
            "insufficient_data": False,
        }),
    ]

    result = await answer_support(
        "Сколько занимает доставка по городу?",
        1,
        order_repo,
        mock_client,
    )

    assert "2–3 рабочих дня" in result.answer
    assert result.sources == ["delivery-1"]
    assert result.handoff is False
    assert result.input_tokens == 200
    assert result.output_tokens == 40

    create = mock_client.chat.completions.create
    assert create.await_count == 2

    first_call = create.call_args_list[0].kwargs
    second_call = create.call_args_list[1].kwargs

    assert first_call["messages"][0]["content"] == PLAN_PROMPT
    assert second_call["messages"][0]["content"] == ANSWER_PROMPT

    payload = json.loads(
        second_call["messages"][1]["content"]
    )

    assert payload["documents"] == [DOCUMENTS[0]]
    order_repo.get_by_id.assert_not_awaited()


# 2. Вопрос о возврате

@pytest.mark.anyio
async def test_return_question(mock_client, order_repo):
    mock_client.chat.completions.create.side_effect = [
        make_response({
            "action": "knowledge",
            "topic": "returns",
        }),
        make_response({
            "answer": "Заявление рассматривает оператор магазина.",
            "sources": ["returns-1"],
            "insufficient_data": False,
        }),
    ]

    result = await answer_support(
        "Как вернуть товар?",
        1,
        order_repo,
        mock_client,
    )

    assert "оператор" in result.answer
    assert result.sources == ["returns-1"]
    assert result.handoff is False
    assert "возврат одобрен" not in result.answer.lower()


# 3. Неизвестный тариф доставки

@pytest.mark.anyio
async def test_unknown_delivery_price(
    mock_client, order_repo
):
    mock_client.chat.completions.create.side_effect = [
        make_response({
            "action": "knowledge",
            "topic": "delivery",
        }),
        make_response({
            "answer": "Стоимость доставки неизвестна.",
            "sources": [],
            "insufficient_data": True,
        }),
    ]

    result = await answer_support(
        "Сколько стоит доставка?",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    assert result.input_tokens == 200
    assert result.output_tokens == 40


# 4. Получение статуса своего заказа

@pytest.mark.anyio
async def test_own_order_status(mock_client, order_repo):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "order",
            "order_id": 5,
        })
    )

    order_repo.get_by_id.return_value = SimpleNamespace(
        id=5,
        user_id=1,
        status="completed",
    )

    result = await answer_support(
        "Где мой заказ номер 5?",
        1,
        order_repo,
        mock_client,
    )

    assert result.answer == "Статус заказа: completed."
    assert result.handoff is False
    assert result.sources == []

    order_repo.get_by_id.assert_awaited_once_with(5)
    mock_client.chat.completions.create.assert_awaited_once()


# 5–6. Чужой и несуществующий заказ

@pytest.mark.anyio
@pytest.mark.parametrize("order", [
    SimpleNamespace(
        id=5,
        user_id=2,
        status="completed",
    ),
    None,
])
async def test_order_not_available(
    mock_client, order_repo, order
):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "order",
            "order_id": 5,
        })
    )

    order_repo.get_by_id.return_value = order

    result = await answer_support(
        "Покажи заказ номер 5",
        1,
        order_repo,
        mock_client,
    )

    assert result.answer == ORDER_NOT_FOUND
    assert "completed" not in result.answer
    assert result.sources == []

    order_repo.get_by_id.assert_awaited_once_with(5)


# 7. Модель пытается подменить пользователя

@pytest.mark.anyio
async def test_model_cannot_change_user_id(
    mock_client, order_repo
):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "order",
            "order_id": 5,
            "user_id": 2,
        })
    )

    result = await answer_support(
        "Покажи заказ пользователя 2",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    order_repo.get_by_id.assert_not_awaited()


# 8. Некорректный JSON модели

@pytest.mark.anyio
async def test_invalid_model_json(mock_client, order_repo):
    mock_client.chat.completions.create.return_value = (
        make_response("invalid json")
    )

    result = await answer_support(
        "Где мой заказ?",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    order_repo.get_by_id.assert_not_awaited()


# 9. Запрещённое или неизвестное действие

@pytest.mark.anyio
@pytest.mark.parametrize("action", [
    "delete_order",
    "update_order",
    "unknown_action",
])
async def test_unknown_action(
    mock_client, order_repo, action
):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": action,
            "order_id": 5,
        })
    )

    result = await answer_support(
        "Удали мой заказ",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    order_repo.get_by_id.assert_not_awaited()
    assert order_repo.mock_calls == []


# 10. Отсутствует номер заказа

@pytest.mark.anyio
async def test_missing_order_id(mock_client, order_repo):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "order",
            "order_id": None,
        })
    )

    result = await answer_support(
        "Где мой заказ?",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    order_repo.get_by_id.assert_not_awaited()


# 11. Неизвестный или неподходящий источник

@pytest.mark.anyio
@pytest.mark.parametrize("sources", [
    ["fake-document"],
    ["returns-1"],
    [],
])
async def test_invalid_sources(
    mock_client, order_repo, sources
):
    mock_client.chat.completions.create.side_effect = [
        make_response({
            "action": "knowledge",
            "topic": "delivery",
        }),
        make_response({
            "answer": "Доставка всегда бесплатная.",
            "sources": sources,
            "insufficient_data": False,
        }),
    ]

    result = await answer_support(
        "Доставка бесплатная?",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    assert "бесплатная" not in result.answer


# 12. Пустая база знаний

@pytest.mark.anyio
async def test_empty_documents(mock_client, order_repo):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "knowledge",
            "topic": "delivery",
        })
    )

    result = await answer_support(
        "Сколько занимает доставка?",
        1,
        order_repo,
        mock_client,
        documents=[],
    )

    assert_operator(result)
    mock_client.chat.completions.create.assert_awaited_once()


# 13. Недоступность API модели

@pytest.mark.anyio
async def test_provider_timeout(mock_client, order_repo):
    mock_client.chat.completions.create.side_effect = (
        APITimeoutError(
            request=httpx.Request(
                "POST",
                "https://example.com",
            )
        )
    )

    result = await answer_support(
        "Сколько занимает доставка?",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    assert result.input_tokens == 0
    assert result.output_tokens == 0


# 14. Передача вопроса оператору

@pytest.mark.anyio
async def test_operator_action(mock_client, order_repo):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "operator",
        })
    )

    result = await answer_support(
        "Измени адрес моего заказа",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    mock_client.chat.completions.create.assert_awaited_once()
    order_repo.get_by_id.assert_not_awaited()


# 15. Пустой или слишком длинный вопрос

@pytest.mark.anyio
@pytest.mark.parametrize("question", [
    "",
    "   ",
    "а" * 1001,
])
async def test_invalid_question(
    mock_client, order_repo, question
):
    result = await answer_support(
        question,
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    mock_client.chat.completions.create.assert_not_awaited()


# Дополнительные проверки для полного покрытия


@pytest.mark.anyio
async def test_order_repository_missing(mock_client):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "order",
            "order_id": 5,
        })
    )

    result = await answer_support(
        "Где заказ 5?",
        1,
        None,
        mock_client,
    )

    assert_operator(result)


@pytest.mark.anyio
async def test_unknown_topic(mock_client, order_repo):
    mock_client.chat.completions.create.return_value = (
        make_response({
            "action": "knowledge",
            "topic": "unknown",
        })
    )

    result = await answer_support(
        "Расскажи про гарантию",
        1,
        order_repo,
        mock_client,
    )

    assert_operator(result)
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize("response_type", [
    "no_choices",
    "incomplete",
    "empty_content",
    "no_usage",
])
async def test_ask_json_invalid_response(
    mock_client, response_type
):
    response = make_response({"action": "operator"})

    if response_type == "no_choices":
        response.choices = []

    elif response_type == "incomplete":
        response.choices[0].finish_reason = "length"

    elif response_type == "empty_content":
        response.choices[0].message.content = None

    elif response_type == "no_usage":
        response.usage = None

    mock_client.chat.completions.create.return_value = response

    with pytest.raises(ValueError):
        await ask_json(
            mock_client,
            PLAN_PROMPT,
            {"question": "Тестовый вопрос"},
        )