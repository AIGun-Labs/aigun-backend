import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestIntelligenceViews(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_request = MagicMock()
        self.mock_request.user_id = "test_user"
        self.mock_request.context.mastercache.backend.hset = AsyncMock()
        self.mock_request.context.mastercache.backend.expire = AsyncMock()
        
        self.mock_query_params = MagicMock()
        self.mock_query_params.model_dump_json.return_value = '{"test": "params"}'
        
        self.mock_page_query = MagicMock()
        self.mock_page_query.page = 1
        self.mock_page_query.page_size = 10
    
    @patch('apps.intelligence.views.list_intelligence')
    async def test_get_intelligences_list(self, mock_list_intelligence):
        mock_list_intelligence.return_value = (["test_data"], 100)
        
        from apps.intelligence.views import get_intelligences_list
        
        response = await get_intelligences_list(self.mock_query_params, self.mock_request, self.mock_page_query)
        
        self.assertEqual(response.data, ["test_data"])
        self.assertEqual(response.total, 100)
        self.mock_request.context.mastercache.backend.hset.assert_called_once()
        self.mock_request.context.mastercache.backend.expire.assert_called_once()
    
    @patch('apps.intelligence.views.retrieve_token')
    async def test_get_token_info(self, mock_retrieve_token):
        mock_retrieve_token.return_value = {"symbol": "BTC"}
        
        from apps.intelligence.views import get_token_info
        
        response = await get_token_info("ethereum", "0x123", None, self.mock_request)
        
        self.assertEqual(response.data, {"symbol": "BTC"})
        mock_retrieve_token.assert_called_once_with(self.mock_request, "ethereum", "0x123")


if __name__ == '__main__':
    unittest.main()