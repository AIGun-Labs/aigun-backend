import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from apps.intelligence.views import router


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.user_id = "test_user"
    request.context.mastercache.backend.hset = AsyncMock()
    request.context.mastercache.backend.expire = AsyncMock()
    return request


@pytest.fixture
def mock_query_params():
    params = MagicMock()
    params.model_dump_json.return_value = '{"test": "params"}'
    return params


@pytest.fixture
def mock_page_query():
    page_query = MagicMock()
    page_query.page = 1
    page_query.page_size = 10
    return page_query


@pytest.mark.asyncio
async def test_get_intelligences_list(mock_request, mock_query_params, mock_page_query, monkeypatch):
    mock_list_intelligence = AsyncMock(return_value=(["test_data"], 100))
    monkeypatch.setattr("apps.intelligence.views.list_intelligence", mock_list_intelligence)
    
    from apps.intelligence.views import get_intelligences_list
    
    response = await get_intelligences_list(mock_query_params, mock_request, mock_page_query)
    
    assert response.data == ["test_data"]
    assert response.total == 100
    mock_request.context.mastercache.backend.hset.assert_called_once()
    mock_request.context.mastercache.backend.expire.assert_called_once()


@pytest.mark.asyncio
async def test_get_token_info(mock_request, monkeypatch):
    mock_retrieve_token = AsyncMock(return_value={"symbol": "BTC"})
    monkeypatch.setattr("apps.intelligence.views.retrieve_token", mock_retrieve_token)
    
    from apps.intelligence.views import get_token_info
    
    response = await get_token_info("ethereum", "0x123", None, mock_request)
    
    assert response.data == {"symbol": "BTC"}
    mock_retrieve_token.assert_called_once_with(mock_request, "ethereum", "0x123")