from unittest.mock import MagicMock
mock_instance = MagicMock()
mock_instance.__enter__.return_value = mock_instance
mock_instance.text.return_value = [{"title": "t", "href": "h", "body": "b"}]
with mock_instance as ddgs:
    results = ddgs.text("query")
    print(results)
