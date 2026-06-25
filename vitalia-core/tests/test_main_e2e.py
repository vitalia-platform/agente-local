# <!-- test_main_e2e.py | Atualizado em: 24-06-2026 18:25:00(GMT-04:00) -->
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@patch('main.build_ollama_client')
def test_orchestrator_builds_correct_topology(mock_client_builder):
    """
    E2E Simulado: Verifica se a topologia Cross-WSL está correta.
    - Arquiteto deve usar o cliente do Nó 1 (Llama 3.2:3b).
    - Engenheiro deve usar o cliente do Nó 2 (Qwen 2.5-coder:7b).
    """
    from main import build_orchestrator

    mock_client = MagicMock()
    mock_client_builder.return_value = mock_client

    team, architect, engineer = build_orchestrator()

    assert mock_client_builder.call_count == 2

    # Primeiro call: Arquiteto no Nó 1 com Llama
    first_call_args = mock_client_builder.call_args_list[0]
    assert "llama3.2:3b" in str(first_call_args)

    # Segundo call: Engenheiro no Nó 2 com Qwen
    second_call_args = mock_client_builder.call_args_list[1]
    assert "qwen2.5-coder:7b" in str(second_call_args)

    # Valida nomes dos agentes
    assert architect.name == "Architect"
    assert engineer.name == "Engineer"


@patch('main.build_ollama_client')
def test_engineer_has_context_limiter(mock_client_builder):
    """
    E2E: Verifica que o Engenheiro foi configurado com BufferedChatCompletionContext
    para proteger a VRAM da GTX 1060 (Nó 2).
    """
    from autogen_core.model_context import HeadAndTailChatCompletionContext
    from main import build_orchestrator

    mock_client_builder.return_value = MagicMock()

    _, _, engineer = build_orchestrator()

    # O engineer deve ter um model_context do tipo HeadAndTail
    assert engineer._model_context is not None
    assert isinstance(engineer._model_context, HeadAndTailChatCompletionContext)


@patch('main.build_ollama_client')
def test_architect_has_web_search_tool(mock_client_builder):
    """E2E: Verifica que o Arquiteto tem a ferramenta web_search registrada."""
    from main import build_orchestrator
    from tools import web_search

    mock_client_builder.return_value = MagicMock()

    _, architect, _ = build_orchestrator()

    tool_names = [t.name for t in architect._tools] if hasattr(architect, '_tools') else []
    assert "web_search" in tool_names


@patch('main.build_ollama_client')
def test_engineer_has_rag_and_sprint_tools(mock_client_builder):
    """E2E: Verifica que o Engenheiro tem as ferramentas save_code_to_rag e update_sprint_state."""
    from main import build_orchestrator

    mock_client_builder.return_value = MagicMock()

    _, _, engineer = build_orchestrator()

    tool_names = [t.name for t in engineer._tools] if hasattr(engineer, '_tools') else []
    assert "save_code_to_rag" in tool_names
    assert "update_sprint_state" in tool_names


@patch('main.build_ollama_client')
def test_agents_use_urls_from_env(mock_client_builder):
    """
    Spec - Critério 5: O main.py deve ler NO1_LOCAL_OLLAMA_URL e NO2_SERVER_IP
    do ambiente, não hardcoded (Art. VI - Zero Hardcoding).\n    As URLs dos nós são injetadas via variáveis de módulo lidas do .env.
    """
    import main as main_module

    mock_client_builder.return_value = MagicMock()

    test_no1_url = "http://test-node1:11434/v1"
    test_no2_url = "http://test-node2:11434/v1"

    # Injeta diretamente nas vars do módulo (evitando reload que perde o mock)
    original_no1 = main_module.NO1_URL
    original_no2 = main_module.NO2_URL
    try:
        main_module.NO1_URL = test_no1_url
        main_module.NO2_URL = test_no2_url

        main_module.build_orchestrator()

        call_urls = [str(c) for c in mock_client_builder.call_args_list]
        assert test_no1_url in str(call_urls[0])
        assert test_no2_url in str(call_urls[1])
    finally:
        main_module.NO1_URL = original_no1
        main_module.NO2_URL = original_no2


def test_ast_chunking_preserves_function_integrity():
    """
    Spec - Critério 2: O AST Chunking não deve cortar funções ao meio.
    Uma função completa deve retornar como chunk único e íntegro.
    """
    from tools import chunk_code_ast

    code = '''
import os

X = 42

def calculate_bmi(weight: float, height: float) -> float:
    """Calcula o IMC."""
    return weight / (height ** 2)

class HealthChecker:
    def check(self, bmi: float) -> str:
        if bmi < 18.5:
            return "Abaixo do peso"
        elif bmi < 25.0:
            return "Peso normal"
        return "Sobrepeso"
'''

    chunks = chunk_code_ast(code)

    # Nenhum chunk deve conter uma função ou classe fragmentada
    for chunk in chunks:
        # Se o chunk começa com 'def' ou 'class', deve ter seu bloco completo
        lines = chunk.strip().split('\n')
        if lines[0].startswith('def ') or lines[0].startswith('class '):
            # Chunk deve conter pelo menos uma linha de corpo (não só a assinatura)
            assert len(lines) > 1, f"Chunk fragmentado detectado: {chunk[:80]}"

    # As funções e classes completas devem aparecer em algum chunk
    all_chunks_text = '\n'.join(chunks)
    assert 'def calculate_bmi' in all_chunks_text
    assert 'class HealthChecker' in all_chunks_text
    assert 'return weight / (height ** 2)' in all_chunks_text
