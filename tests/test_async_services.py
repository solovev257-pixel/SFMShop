"""Проверки параллельной обработки и HTTP без внешних запросов."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.services import async_service, order_processor


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def session():
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"status": "new"})
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.get.return_value = context
    session.close = AsyncMock()
    return session


@pytest.mark.anyio
@pytest.mark.parametrize("status, expected", [(200, {"status": "new"}), (503, None)])
async def test_fetch_success_and_http_error(session, status, expected):
    session.get.return_value.__aenter__.return_value.status = status
    assert await async_service.fetch_with_session(session, "https://example.test") == expected
    with patch.object(async_service.aiohttp, "ClientSession", return_value=session):
        assert await async_service.fetch_url_async("https://example.test") == expected


@pytest.mark.anyio
async def test_fetch_network_error(session):
    session.get.side_effect = aiohttp.ClientConnectionError("offline")
    assert await async_service.fetch_with_session(session, "https://example.test") is None
    with patch.object(async_service.aiohttp, "ClientSession", return_value=session):
        assert await async_service.fetch_url_async("https://example.test") is None


@pytest.mark.anyio
async def test_parallel_and_sequential_requests(session):
    with patch.object(async_service.aiohttp, "ClientSession", return_value=session):
        results = await async_service.compare_parallel_and_sequential(["https://example.test"] * 2)
    assert results == [{"status": "new"}] * 2
    assert session.get.call_count == 4


@pytest.mark.anyio
async def test_order_processing_reports_each_failure():
    with patch.object(async_service.asyncio, "sleep", new_callable=AsyncMock), \
            patch.object(async_service.time, "sleep"):
        results = await async_service.process_orders_async([1, 25])
        sync_results = async_service.process_orders_sync([1, 25])
    assert results == sync_results
    assert results[0] == {"order_id": 1, "status": "completed", "items": 2, "total": 700}
    assert results[1]["status"] == "failed"


@pytest.mark.anyio
@pytest.mark.parametrize("own_session", [True, False])
async def test_fetch_details_closes_only_owned_session(session, own_session):
    with patch.object(async_service.aiohttp, "ClientSession", return_value=session):
        result = await async_service.fetch_order_details_async(1, None if own_session else session)
    assert result == {"status": "new"}
    assert session.close.await_count == int(own_session)


@pytest.mark.anyio
@pytest.mark.parametrize("error", [TimeoutError(), aiohttp.ClientConnectionError()])
async def test_fetch_details_handles_network_failure(session, error):
    session.get.side_effect = error
    with patch.object(async_service.aiohttp, "ClientSession", return_value=session):
        assert await async_service.fetch_order_details_async(1) is None
    session.close.assert_awaited_once()


@pytest.mark.anyio
async def test_fetch_details_handles_http_failure(session):
    session.get.return_value.__aenter__.return_value.status = 404
    assert await async_service.fetch_order_details_async(999, session) is None


@pytest.mark.anyio
async def test_task_group_success():
    with patch.object(order_processor.asyncio, "sleep", new_callable=AsyncMock):
        result = await order_processor.process_order_tg(101)
    assert result == {
        "order_id": 101, "status": "ready",
        "validation": {"order_id": 101, "valid": True},
        "reservation": {"order_id": 101, "reserved": True},
        "address": {"order_id": 101, "address_valid": True},
    }


@pytest.mark.anyio
@pytest.mark.parametrize("error, status", [(ValueError("invalid"), "validation_error"),
                                         (ConnectionError("offline"), "service_error")])
async def test_task_group_failure(error, status):
    with patch.object(order_processor, "validate_order", new_callable=AsyncMock, side_effect=error), \
            patch.object(order_processor.asyncio, "sleep", new_callable=AsyncMock):
        result = await order_processor.process_order_tg(101)
    assert result["status"] == status
    assert result["errors"] == [str(error)]
