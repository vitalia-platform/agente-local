# test_tools.py | Atualizado em: 26-06-2026 12:08:18(GMT-04:00)
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from tools import update_sprint_state, save_code_to_rag, web_search
except ImportError:
    pass

@patch('tools.redis.Redis')
def test_update_sprint_state(mock_redis):
    """Testa a persistência do estado da sprint no Redis."""
    mock_client = MagicMock()
    mock_redis.from_url.return_value = mock_client
    
    try:
        result = update_sprint_state("Implementar testes", "CONCLUIDO")
        
        mock_client.hset.assert_called_once()
        args, kwargs = mock_client.hset.call_args
        assert args[0] == "vitalia:sprint_state"
        assert kwargs["mapping"]["task"] == "Implementar testes"
        assert kwargs["mapping"]["status"] == "CONCLUIDO"
        assert "Sucesso" in result
    except NameError:
        pytest.fail("update_sprint_state not implemented")

@patch('tools.psycopg2.connect')
@patch('tools.requests.post')
def test_save_code_to_rag(mock_post, mock_connect):
    """Testa o AST Chunking e a inserção no pgvector."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.1] * 768}
    mock_post.return_value = mock_response
    
    code_content = '''
def hello_world():
    print("Test")
    return True
'''
    try:
        result = save_code_to_rag("test.py", code_content)
        
        assert mock_cursor.execute.called
        args, kwargs = mock_cursor.execute.call_args
        assert "hello_world" in args[1][1]
        assert "Sucesso" in result
    except NameError:
        pytest.fail("save_code_to_rag not implemented")

@patch('tools.DDGS')
def test_web_search(mock_ddgs):
    """Testa a integração da busca web."""
    mock_instance = MagicMock()
    mock_ddgs.return_value = mock_instance
    mock_instance.text.return_value = [
        {"title": "AutoGen Docs", "body": "Example of AutoGen", "href": "https://microsoft.github.io/autogen/"}
    ]
    
    try:
        result = web_search("autogen examples")
        assert "AutoGen Docs" in result
        assert "Example of AutoGen" in result
    except NameError:
        pytest.fail("web_search not implemented")
