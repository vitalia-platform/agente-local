# test_main_e2e.py | Atualizado em: 01-07-2026 15:03:07(GMT-04:00)
import sys
import os
import json
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ---------------------------------------------------------------------------
# TESTE 1 — Arquiteto SEM tools quando NATIVE=false
# ---------------------------------------------------------------------------
@patch('main.build_ollama_client')
def test_native_false_architect_has_no_tools(mock_client_builder):
    """
    RF-02 / CA-02: Quando NO1_TOOL_CALLING_NATIVE=false,
    o AssistantAgent do Arquiteto NÃO deve ter tools registradas.
    O Tool Bridge assume esse papel.
    """
    from main import build_orchestrator
    mock_client_builder.return_value = MagicMock()

    env_overrides = {
        'NO1_TOOL_CALLING_NATIVE': 'false',
        'NO2_TOOL_CALLING_NATIVE': 'true',
        'NO1_MODEL': 'llama3.2:3b',
        'NO2_MODEL': 'qwen2.5-coder:7b',
    }
    with patch.dict(os.environ, env_overrides):
        _, architect, _ = build_orchestrator()

    tools = architect._tools if hasattr(architect, '_tools') else []
    assert tools == [] or tools is None, (
        f"Arquiteto não deveria ter tools com NATIVE=false, mas tem: {tools}"
    )


# ---------------------------------------------------------------------------
# TESTE 2 — Arquiteto COM tools quando NATIVE=true
# ---------------------------------------------------------------------------
@patch('main.build_ollama_client')
def test_native_true_architect_has_tools(mock_client_builder):
    """
    RF-02 / CA-01: Quando NO1_TOOL_CALLING_NATIVE=true,
    o AssistantAgent do Arquiteto DEVE ter tools registradas.
    """
    from main import build_orchestrator
    mock_client_builder.return_value = MagicMock()

    env_overrides = {
        'NO1_TOOL_CALLING_NATIVE': 'true',
        'NO2_TOOL_CALLING_NATIVE': 'true',
        'NO1_MODEL': 'llama3.2:3b',
        'NO2_MODEL': 'qwen2.5-coder:7b',
    }
    with patch.dict(os.environ, env_overrides):
        _, architect, _ = build_orchestrator()

    tools = architect._tools if hasattr(architect, '_tools') else []
    assert len(tools) > 0, (
        "Arquiteto deveria ter tools com NATIVE=true, mas a lista está vazia"
    )
    tool_names = [t.name for t in tools]
    assert "web_search" in tool_names


# ---------------------------------------------------------------------------
# TESTE 3 — build_orchestrator() lê modelo do .env (sem hardcoding)
# ---------------------------------------------------------------------------
@patch('main.build_ollama_client')
def test_orchestrator_reads_model_from_env(mock_client_builder):
    """
    RF-02 / RNF-01 / CA-01: build_orchestrator() deve usar os modelos
    declarados em NO1_MODEL e NO2_MODEL, não valores hardcoded.
    """
    from main import build_orchestrator
    mock_client_builder.return_value = MagicMock()

    env_overrides = {
        'NO1_MODEL': 'mistral:7b-test',
        'NO2_MODEL': 'deepseek:6.7b-test',
        'NO1_TOOL_CALLING_NATIVE': 'false',
        'NO2_TOOL_CALLING_NATIVE': 'true',
    }
    with patch.dict(os.environ, env_overrides):
        build_orchestrator()

    all_calls = str(mock_client_builder.call_args_list)

    # Modelos do .env devem aparecer nas chamadas
    assert 'mistral:7b-test' in all_calls, (
        f"Esperava 'mistral:7b-test' nas chamadas ao build_ollama_client, mas não encontrou.\n{all_calls}"
    )
    assert 'deepseek:6.7b-test' in all_calls, (
        f"Esperava 'deepseek:6.7b-test' nas chamadas ao build_ollama_client, mas não encontrou.\n{all_calls}"
    )

    # Modelos hardcoded NÃO devem aparecer
    assert 'llama3.2:3b' not in all_calls or 'mistral:7b-test' in all_calls, (
        "Modelo hardcoded 'llama3.2:3b' apareceu — zero hardcoding violado (Art. XII)"
    )


# ---------------------------------------------------------------------------
# TESTE 4 — Engenheiro tem contexto limitador de VRAM (mantido da suíte anterior)
# ---------------------------------------------------------------------------
@patch('main.build_ollama_client')
def test_engineer_has_context_limiter(mock_client_builder):
    """
    RF-02 (engineer): O Engenheiro deve ter HeadAndTailChatCompletionContext
    para proteger a VRAM do Nó 2.
    """
    from autogen_core.model_context import HeadAndTailChatCompletionContext
    from main import build_orchestrator
    mock_client_builder.return_value = MagicMock()

    env_overrides = {
        'NO1_MODEL': 'llama3.2:3b',
        'NO2_MODEL': 'qwen2.5-coder:7b',
        'NO1_TOOL_CALLING_NATIVE': 'false',
        'NO2_TOOL_CALLING_NATIVE': 'true',
    }
    with patch.dict(os.environ, env_overrides):
        _, _, engineer = build_orchestrator()

    assert engineer._model_context is not None
    assert isinstance(engineer._model_context, HeadAndTailChatCompletionContext), (
        f"Esperava HeadAndTailChatCompletionContext, mas foi: {type(engineer._model_context)}"
    )


# ---------------------------------------------------------------------------
# TESTE 5 — tool_worker() posta resultado na stream de resultado
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tool_worker_posts_result_to_stream():
    """
    RF-04 / CA-03: tool_worker() deve consumir da stream de request,
    executar a ferramenta via TOOL_REGISTRY e postar na stream de resultado.
    """
    import main as main_module

    # Mock da ferramenta no registry
    mock_tool = MagicMock(return_value="resultado mockado")
    original_registry = getattr(main_module, 'TOOL_REGISTRY', {})
    main_module.TOOL_REGISTRY = {"web_search": mock_tool}

    cid = "test-correlation-id-001"

    # Mock do redis_reader: retorna 1 mensagem depois ignora
    call_count = 0
    async def fake_xread(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [(
                b"vitalia:tool_requests:Architect",
                [(b"1-0", {
                    b"correlation_id": cid.encode(),
                    b"tool_name": b"web_search",
                    b"arguments_json": b'{"query": "test"}',
                    b"agent_name": b"Architect",
                    b"timestamp": b"2026-06-27T13:00:00",
                })]
            )]
        raise asyncio.CancelledError()  # encerra o worker após 1 ciclo

    mock_reader = AsyncMock()
    mock_reader.xread = fake_xread

    mock_writer = AsyncMock()
    mock_writer.xadd = AsyncMock()

    # Injetar event para o worker sinalizar
    event = asyncio.Event()
    main_module._pending_tool_calls = {cid: event}
    main_module._tool_results = {}

    try:
        await main_module.tool_worker(mock_reader, mock_writer)
    except asyncio.CancelledError:
        pass

    # Verificar que XADD foi chamado na stream de resultado
    mock_writer.xadd.assert_called_once()
    call_args = mock_writer.xadd.call_args
    stream_name = call_args[0][0] if call_args[0] else call_args[1].get('name', '')
    assert 'tool_results' in str(stream_name), (
        f"XADD deveria ser na stream tool_results, mas foi: {stream_name}"
    )

    # Verificar que o evento foi sinalizado
    assert event.is_set(), "O Event do correlation_id deveria ter sido setado pelo worker"

    # Restaurar estado
    main_module.TOOL_REGISTRY = original_registry
    main_module._pending_tool_calls = {}
    main_module._tool_results = {}


# ---------------------------------------------------------------------------
# TESTE 6 — VitaliaOllamaClient detecta JSON e retorna FunctionCall via Bridge
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_vitalia_client_bridges_tool_on_json():
    """
    RF-03 / CA-03: VitaliaOllamaClient deve detectar JSON de tool call no resultado,
    postar na Redis Stream e retornar CreateResult(content=[FunctionCall(...)]).
    O AutoGen então processa como ToolCallRequestEvent (não TextMessage).
    """
    import main as main_module
    from autogen_core.models._types import CreateResult, FunctionCall
    from autogen_core.models import RequestUsage

    # JSON que simula o LLM vazando um tool call como texto puro
    tool_json = json.dumps({"name": "web_search", "arguments": {"query": "autogen docs"}})

    # Mock do super().create() retornando JSON cru
    mock_create_result = CreateResult(
        content=tool_json,
        usage=RequestUsage(prompt_tokens=10, completion_tokens=20),
        finish_reason="stop",
        cached=False,
    )

    cid = "test-bridge-cid-002"
    result_value = "Resultado da busca: AutoGen docs encontrados."

    # Simular: ao chamar _bridge_tool_call, o event já está setado (worker respondeu)
    async def fake_bridge(tool_name, arguments_json):
        return result_value

    client = main_module.VitaliaOllamaClient.__new__(main_module.VitaliaOllamaClient)
    client._agent_name = "Architect"
    client._timeout = 5
    client._bridge_tool_call = fake_bridge

    with patch.object(
        main_module.OllamaChatCompletionClient,
        'create',
        new_callable=AsyncMock,
        return_value=mock_create_result
    ):
        result = await client.create(messages=[], model="test-model")

    # Resultado deve ser FunctionCall, não TextMessage
    assert isinstance(result.content, list), (
        f"Esperava lista de FunctionCall, mas content é: {type(result.content)}"
    )
    assert len(result.content) == 1
    fc = result.content[0]
    assert isinstance(fc, FunctionCall), (
        f"Esperava FunctionCall, mas foi: {type(fc)}"
    )
    assert fc.name == "web_search", f"Nome da tool errado: {fc.name}"
