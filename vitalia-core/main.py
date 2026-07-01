# main.py | Atualizado em: 01-07-2026 15:03:06(GMT-04:00)
import os
import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_core.models._types import CreateResult, FunctionCall
from autogen_core.model_context import HeadAndTailChatCompletionContext
from autogen_agentchat.ui import Console

from tools import save_code_to_rag, update_sprint_state, web_search, \
                  read_working_memory, query_audit_log, load_dynamic_skill

# ---------------------------------------------------------------------------
# URLs dos nós (lidas do .env — Art. XII: Zero Hardcoding)
# ---------------------------------------------------------------------------
NO1_URL = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434/v1")
NO2_URL = os.getenv("NO2_SERVER_IP", "http://server-ip:11434/v1")

# URL do Redis para o Tool Bridge
REDIS_URL = (
    f"redis://:{os.getenv('REDIS_PASSWORD', '')}@"
    f"localhost:{os.getenv('REDIS_PORT', '6379')}/0"
)

# ---------------------------------------------------------------------------
# Registro de ferramentas disponíveis para o Tool Bridge (RF-04)
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict = {
    "web_search":          web_search,
    "save_code_to_rag":    save_code_to_rag,
    "update_sprint_state": update_sprint_state,
    "read_working_memory": read_working_memory,
    "query_audit_log":     query_audit_log,
    "load_dynamic_skill":  load_dynamic_skill,
}

# ---------------------------------------------------------------------------
# Estado compartilhado do Tool Bridge (por processo)
# ---------------------------------------------------------------------------
_pending_tool_calls: dict = {}  # correlation_id -> asyncio.Event
_tool_results: dict = {}        # correlation_id -> result string
_r_writer = None                # Conexão Redis para escrita (injetada em run_vitalia)


# ---------------------------------------------------------------------------
# VitaliaOllamaClient — Tool Bridge para nós sem Tool Calling nativo (RF-03)
# ---------------------------------------------------------------------------
class VitaliaOllamaClient(OllamaChatCompletionClient):
    """
    Wrapper para nós com TOOL_CALLING_NATIVE=false.
    Intercepta JSONs crus de tool call vazados pelo LLM e os executa
    via Tool Bridge (Redis Streams), retornando FunctionCall ao AutoGen.
    """

    def __init__(self, agent_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_name = agent_name
        self._timeout = int(os.getenv("TOOL_BRIDGE_TIMEOUT_SEC", "30"))

    def _is_tool_call_json(self, content: str) -> bool:
        """Detecta se o conteúdo é um JSON de tool call {name, arguments}."""
        content = content.strip()
        if not (content.startswith("{") and content.endswith("}")):
            return False
        try:
            data = json.loads(content)
            return isinstance(data, dict) and "name" in data and "arguments" in data
        except json.JSONDecodeError:
            return False

    async def _bridge_tool_call(self, tool_name: str, arguments_json: str) -> str:
        """
        Posta o pedido de execução na Redis Stream e aguarda o resultado.
        Bloqueante no contexto asyncio (usa asyncio.Event).
        """
        global _r_writer
        cid = str(uuid.uuid4())
        event = asyncio.Event()
        _pending_tool_calls[cid] = event

        try:
            if _r_writer is None:
                return (
                    f"Tool unavailable: Redis connection not initialized. Tool: {tool_name}"
                )
            await _r_writer.xadd(
                f"vitalia:tool_requests:{self._agent_name}",
                {
                    "correlation_id": cid,
                    "tool_name": tool_name,
                    "arguments_json": arguments_json,
                    "agent_name": self._agent_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),

                }
            )
            await asyncio.wait_for(event.wait(), timeout=self._timeout)
            return _tool_results.pop(cid, f"Error: result missing for {cid}")
        except asyncio.TimeoutError:
            return (
                f"Tool unavailable: worker timeout after {self._timeout}s. Tool: {tool_name}"
            )
        except Exception as e:
            return f"Tool unavailable: Redis connection failed. Tool: {tool_name}. Error: {e}"
        finally:
            _pending_tool_calls.pop(cid, None)

    async def create(self, *args, **kwargs) -> CreateResult:
        result = await super().create(*args, **kwargs)

        if isinstance(result.content, str) and self._is_tool_call_json(result.content):
            data = json.loads(result.content.strip())
            tool_name = data["name"]
            args_val = data["arguments"]
            arguments_json = (
                json.dumps(args_val) if isinstance(args_val, dict) else str(args_val)
            )
            tool_result_str = await self._bridge_tool_call(tool_name, arguments_json)
            tool_call = FunctionCall(
                id=str(uuid.uuid4())[:8],
                name=tool_name,
                arguments=arguments_json,
            )
            result.content = [tool_call]

        return result

    async def create_stream(self, *args, **kwargs):
        """Passthrough de stream — bridge não se aplica ao streaming."""
        async for chunk in super().create_stream(*args, **kwargs):
            yield chunk


# ---------------------------------------------------------------------------
# build_ollama_client — Fábrica de clientes hardware-adaptive (RF-02, DE-06)
# ---------------------------------------------------------------------------
def build_ollama_client(
    base_url: str, model: str, native: bool = True, agent_name: str = ""
):
    """
    Retorna o cliente correto conforme a capacidade do nó:
    - native=True  → OllamaChatCompletionClient (tool calling nativo)
    - native=False → VitaliaOllamaClient (Tool Bridge via Redis Streams)
    """
    host = base_url.replace("/v1", "")
    model_info = {
        "vision": False,
        "function_calling": True,
        "json_output": False,
        "family": "unknown",
    }
    if native:
        return OllamaChatCompletionClient(model=model, host=host, model_info=model_info)
    else:
        return VitaliaOllamaClient(
            agent_name=agent_name, model=model, host=host, model_info=model_info
        )


# ---------------------------------------------------------------------------
# build_orchestrator — Topologia hardware-adaptive (RF-02)
# ---------------------------------------------------------------------------
def build_orchestrator():
    """
    Constrói o GroupChat com topologia Cross-WSL adaptativa.
    Lê NO1_MODEL, NO2_MODEL, NO1_TOOL_CALLING_NATIVE, NO2_TOOL_CALLING_NATIVE
    do .env — sem nenhum nome de modelo hardcoded (Art. XII).
    """
    # Perfis de hardware — fonte da verdade: .env
    no1_model  = os.getenv("NO1_MODEL")
    no2_model  = os.getenv("NO2_MODEL")
    native_no1 = os.getenv("NO1_TOOL_CALLING_NATIVE", "false").lower() == "true"
    native_no2 = os.getenv("NO2_TOOL_CALLING_NATIVE", "true").lower()  == "true"

    # ── Arquiteto (Nó 1) ──────────────────────────────────────────────────
    architect_client = build_ollama_client(NO1_URL, no1_model, native_no1, "Architect")
    architect_tools  = (
        [web_search, query_audit_log, load_dynamic_skill] if native_no1 else []
    )
    architect = AssistantAgent(
        name="Architect",
        model_client=architect_client,
        tools=architect_tools,
        description=(
            "Pensa sobre a estrutura, toma decisões de design e orienta o Engenheiro. "
            "Usa busca na web para referências."
        ),
        system_message=(
            "Você é o Arquiteto Vitalia. Analise os requisitos, defina a estrutura e oriente "
            "o Engenheiro com clareza. Use `web_search` para consultar documentações atualizadas. "
            "Se o Engenheiro propor código sem ter consultado o contexto (read_working_memory), "
            "REJEITE a resposta e ordene a leitura da memória. "
            "Use `query_audit_log` caso precise lembrar do contexto de turnos muito antigos. "
            "Responda com TERMINATE quando o objetivo da sprint estiver concluído. "
            "[CRITICAL] NUNCA escreva blocos de código JSON simulando a chamada de ferramentas. "
            "Sempre utilize o mecanismo NATIVO de Function Calling da API para acionar ferramentas."
        ),
    )

    # ── Engenheiro (Nó 2) ─────────────────────────────────────────────────
    # Limitador de contexto: protege a VRAM do Nó 2
    engineer_context = HeadAndTailChatCompletionContext(head_size=1, tail_size=20)
    engineer_client  = build_ollama_client(NO2_URL, no2_model, native_no2, "Engineer")
    engineer_tools   = (
        [save_code_to_rag, update_sprint_state, read_working_memory, load_dynamic_skill]
        if native_no2 else []
    )
    engineer = AssistantAgent(
        name="Engineer",
        model_client=engineer_client,
        tools=engineer_tools,
        model_context=engineer_context,
        description="Escreve o código baseado no plano do Arquiteto, salva no RAG e atualiza a sprint.",
        system_message=(
            "Você é o Engenheiro Vitalia. "
            "[MANDATORY] Você DEVE SEMPRE usar a ferramenta `read_working_memory` antes de "
            "escrever ou modificar código, para garantir que você tem o contexto atualizado. "
            "O Arquiteto rejeitará seu código se não fizer isso. "
            "Sempre salve o código gerado usando `save_code_to_rag` e atualize o progresso "
            "com `update_sprint_state`. Responda com TERMINATE quando a tarefa estiver concluída. "
            "[CRITICAL] NUNCA escreva blocos de código JSON simulando a chamada de ferramentas. "
            "Sempre utilize o mecanismo NATIVO de Function Calling da API para acionar ferramentas."
        ),
    )

    # ── Critério de parada ────────────────────────────────────────────────
    termination = (
        MaxMessageTermination(max_messages=10) | TextMentionTermination("TERMINATE")
    )
    team = RoundRobinGroupChat(
        participants=[architect, engineer],
        termination_condition=termination,
    )

    return team, architect, engineer


# ---------------------------------------------------------------------------
# tool_worker — Worker assíncrono do Tool Bridge (RF-04)
# ---------------------------------------------------------------------------
async def _process_tool_request(fields: dict, r_writer) -> None:
    """Executa uma ferramenta e posta o resultado na stream de resultado."""
    cid        = fields.get(b"correlation_id", b"").decode()
    tool_name  = fields.get(b"tool_name", b"").decode()
    agent_name = fields.get(b"agent_name", b"Architect").decode()
    args_json  = fields.get(b"arguments_json", b"{}").decode()
    t_start    = time.monotonic()
    error_str  = ""

    try:
        fn = TOOL_REGISTRY.get(tool_name)
        if fn is None:
            result = f"Error: unknown tool '{tool_name}'"
            error_str = result
        else:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: fn(**json.loads(args_json))
            )
    except Exception as e:
        result = f"Error executing {tool_name}: {str(e)}"
        error_str = result

    duration_ms = int((time.monotonic() - t_start) * 1000)

    await r_writer.xadd(
        f"vitalia:tool_results:{agent_name}",
        {
            "correlation_id": cid,
            "result":         str(result),
            "error":          error_str,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "duration_ms":    str(duration_ms),
        }
    )

    # Sinalizar o Event do wrapper que está esperando
    if cid in _pending_tool_calls:
        _tool_results[cid] = str(result)
        _pending_tool_calls[cid].set()

    # Auditoria
    try:
        from logger import logger
        logger.log_event("tool_bridge_exec", "tool_worker", {
            "tool_name":      tool_name,
            "agent_name":     agent_name,
            "correlation_id": cid,
            "duration_ms":    duration_ms,
            "error":          error_str,
        })
    except Exception:
        pass


async def tool_worker(r_reader, r_writer) -> None:
    """
    asyncio.Task independente que monitora as streams de request de todas os agentes,
    executa as ferramentas via TOOL_REGISTRY e posta resultados.
    Nunca bloqueia o loop do AutoGen.
    """
    streams_to_watch = {
        "vitalia:tool_requests:Architect": "$",
        "vitalia:tool_requests:Engineer":  "$",
    }
    while True:
        try:
            messages = await r_reader.xread(
                streams=streams_to_watch, block=500, count=10
            )
            if not messages:
                continue
            for stream_name, stream_messages in messages:
                stream_key = (
                    stream_name.decode() if isinstance(stream_name, bytes) else stream_name
                )
                for msg_id, fields in stream_messages:
                    streams_to_watch[stream_key] = (
                        msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                    )
                    await _process_tool_request(fields, r_writer)
        except asyncio.CancelledError:
            break
        except Exception as e:
            try:
                from logger import logger
                logger.log_event("system_log", "tool_worker", {"error": str(e)})
            except Exception:
                pass


# ---------------------------------------------------------------------------
# run_vitalia — Ponto de entrada da orquestração (RF-05)
# ---------------------------------------------------------------------------
async def run_vitalia(task: str):
    """Executa uma tarefa no orquestrador Vitalia Cross-WSL."""
    global _r_writer

    native_no1 = os.getenv("NO1_TOOL_CALLING_NATIVE", "false").lower() == "true"
    native_no2 = os.getenv("NO2_TOOL_CALLING_NATIVE", "true").lower()  == "true"

    r_writer = r_reader = worker_task = None
    try:
        # Lançar o worker apenas se algum nó precisar do Tool Bridge
        if not native_no1 or not native_no2:
            import redis.asyncio as redis_async
            r_writer = redis_async.Redis.from_url(REDIS_URL)
            r_reader = redis_async.Redis.from_url(REDIS_URL)
            _r_writer = r_writer  # disponibiliza para VitaliaOllamaClient
            worker_task = asyncio.create_task(tool_worker(r_reader, r_writer))

        team, _, _ = build_orchestrator()
        print(f"🚀 Orquestrador Vitalia iniciado. Tarefa: {task}")

        from logger import logger

        async def log_and_yield(stream):
            async for message in stream:
                source = getattr(message, "source", "unknown")
                msg_type_name = type(message).__name__

                usage = getattr(message, "models_usage", None)
                if usage:
                    logger.log_event("telemetry", source, {
                        "prompt_tokens":      getattr(usage, "prompt_tokens", 0),
                        "completion_tokens":  getattr(usage, "completion_tokens", 0),
                    })

                if msg_type_name == "TextMessage":
                    logger.log_event("conversation", source, {"text": message.content})
                elif msg_type_name == "ToolCallRequestEvent":
                    calls = (
                        [{"name": c.name, "arguments": c.arguments} for c in message.content]
                        if isinstance(message.content, list) else str(message.content)
                    )
                    logger.log_event("tool_call", source, {"request": calls})
                elif msg_type_name == "ToolCallExecutionEvent":
                    results = (
                        [{"name": r.name, "content": r.content} for r in message.content]
                        if isinstance(message.content, list) else str(message.content)
                    )
                    logger.log_event("tool_call", source, {"execution_result": results})
                else:
                    content = getattr(message, "content", "")
                    extra_data = {
                        "event_class": msg_type_name,
                        "content": str(content),
                    }
                    if hasattr(message, "stop_reason"):
                        extra_data["stop_reason"] = str(getattr(message, "stop_reason", ""))
                    if hasattr(message, "messages"):
                        extra_data["num_messages"] = len(message.messages)
                    
                    logger.log_event("system_log", source, extra_data)

                yield message

        result = await Console(log_and_yield(team.run_stream(task=task)))
        return result

    finally:
        if worker_task:
            worker_task.cancel()
        if r_writer:
            await r_writer.aclose()
        if r_reader:
            await r_reader.aclose()
        _r_writer = None


if __name__ == "__main__":
    asyncio.run(run_vitalia("Implemente uma função Python para calcular o IMC e salve no RAG."))
    import sys
    sys.exit(0)
