import os
import sys
import pytest
import psycopg2
import redis

# Adiciona o diretório superior ao sys.path para importações locais funcionarem
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools import save_code_to_rag, read_working_memory, DB_URL
from config_manager import config

TEST_FILEPATH = "test_rag_e2e_fake.py"
TEST_CONTENT = "def test_func():\n    return 'TDD E2E Observability'"

@pytest.fixture
def db_connection():
    conn = psycopg2.connect(DB_URL)
    yield conn
    # Teardown: Sanitização E2E
    cur = conn.cursor()
    cur.execute("DELETE FROM code_vectors WHERE filepath = %s", (TEST_FILEPATH,))
    conn.commit()
    cur.close()
    conn.close()

@pytest.fixture
def redis_connection():
    r = redis.Redis.from_url(config.get_redis_url(), decode_responses=True)
    yield r
    # Teardown
    r.delete(f"vitalia:hot_rag:{TEST_FILEPATH}")

def test_save_code_to_rag_e2e(db_connection, redis_connection):
    """
    Testa a função save_code_to_rag em modo E2E (banco real e Ollama real).
    """
    # 1. Executa a ferramenta
    result = save_code_to_rag(TEST_FILEPATH, TEST_CONTENT)
    
    # 2. Verifica se a ferramenta não engoliu erros silenciosamente
    assert "Sucesso" in result, f"A ferramenta falhou e retornou: {result}"
    
    # 3. Verifica o Hot Cache (Redis)
    cached_content = read_working_memory(TEST_FILEPATH)
    assert cached_content == TEST_CONTENT, "O conteúdo não foi salvo corretamente no Redis."
    
    # 4. Verifica o Banco Frio (PostgreSQL)
    cur = db_connection.cursor()
    cur.execute("SELECT content FROM code_vectors WHERE filepath = %s", (TEST_FILEPATH,))
    rows = cur.fetchall()
    
    assert len(rows) > 0, "O banco de dados não contém os vetores inseridos."
    assert rows[0][0] == TEST_CONTENT, "O conteúdo inserido no banco está incorreto."
    cur.close()
