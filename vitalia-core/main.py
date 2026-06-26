# main.py | Atualizado em: 26-06-2026 12:08:18(GMT-04:00)
import os
import asyncio
import json
import uuid
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_core.models._types import CreateResult, FunctionCall
from autogen_agentchat.ui import Console

from tools import save_code_to_rag, update_sprint_state, web_search, read_working_memory, query_audit_log

# Configurações lidas do .env (Zero Hardcoding - Art. VI)
NO1_URL = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434/v1")
NO2_URL = os.getenv("NO2_SERVER_IP", "http://server-ip:11434/v1")


class VitaliaOllamaClient(OllamaChatCompletionClient):
    """
    Wrapper customizado para forçar a detecção de JSONs crus (Manual Tool Calling leak)
    e transformá-los em objetos FunctionCall nativos para o AutoGen.
    """
    def _parse_content_for_tool(self, result: CreateResult) -> CreateResult:
        if isinstance(result.content, str):
            content_str = result.content.strip()
            if content_str.startswith("{") and content_str.endswith("}"):
                try:
                    data = json.loads(content_str)
                    if isinstance(data, dict) and "name" in data and "arguments" in data:
                        # Se arguments já é dict, converte pra string json (padrão OpenAI)
                        args_str = json.dumps(data["arguments"]) if isinstance(data["arguments"], dict) else str(data["arguments"])
                        tool_call = FunctionCall(
                            id=str(uuid.uuid4())[:8],
                            name=data["name"],
                            arguments=args_str
                        )
                        result.content = [tool_call]
                except json.JSONDecodeError:
                    pass
        return result

    async def create(self, *args, **kwargs) -> CreateResult:
        result = await super().create(*args, **kwargs)
        return self._parse_content_for_tool(result)
        
    async def create_stream(self, *args, **kwargs):
        async for chunk in super().create_stream(*args, **kwargs):
            if isinstance(chunk, CreateResult):
                yield self._parse_content_for_tool(chunk)
            else:
                yield chunk

def build_ollama_client(base_url: str, model: str) -> VitaliaOllamaClient:
    """Constrói um cliente Ollama (Nativo Wrapper) para melhor suporte a function calling em LLMs locais."""
    host = base_url.replace("/v1", "")
    return VitaliaOllamaClient(
        model=model,
        host=host,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
        }
    )


def build_orchestrator():
    """Constrói o GroupChat com topologia Cross-WSL: Arquiteto no Nó 1, Engenheiro no Nó 2."""

    # Arquiteto no Nó 1 (Llama 3.2:3b - RAM/Swap do Notebook)
    architect_client = build_ollama_client(NO1_URL, "llama3.2:3b")
    architect = AssistantAgent(
        name="Architect",
        model_client=architect_client,
        tools=[web_search, query_audit_log],
        description="Pensa sobre a estrutura, toma decisões de design e orienta o Engenheiro. Usa busca na web para referências.",
        system_message=(
            "Você é o Arquiteto Vitalia. Analise os requisitos, defina a estrutura e oriente "
            "o Engenheiro com clareza. Use `web_search` para consultar documentações atualizadas. "
            "Se o Engenheiro propor código sem ter consultado o contexto (read_working_memory), "
            "REJEITE a resposta e ordene a leitura da memória. "
            "Use `query_audit_log` caso precise lembrar do contexto de turnos muito antigos. "
            "Responda com TERMINATE quando o objetivo da sprint estiver concluído. "
            "[CRITICAL] NUNCA escreva blocos de código JSON simulando a chamada de ferramentas no seu texto. "
            "Sempre utilize o mecanismo NATIVO de Function Calling da API para acionar ferramentas."
        )
    )

    # Engenheiro no Nó 2 (Qwen 2.5-coder:7b - VRAM exclusiva da GTX 1060)
    # Limitador de contexto: Head 1 (Prompt), Tail N. Limitado a 7000 tokens na GTX 1060.
    from autogen_core.model_context import HeadAndTailChatCompletionContext
    engineer_context = HeadAndTailChatCompletionContext(head_size=1, tail_size=20) # 20 msgs tail

    engineer_client = build_ollama_client(NO2_URL, "qwen2.5-coder:7b")
    engineer = AssistantAgent(
        name="Engineer",
        model_client=engineer_client,
        tools=[save_code_to_rag, update_sprint_state, read_working_memory],
        model_context=engineer_context,
        description="Escreve o código baseado no plano do Arquiteto, salva no RAG e atualiza a sprint.",
        system_message=(
            "Você é o Engenheiro Vitalia. "
            "[MANDATORY] Você DEVE SEMPRE usar a ferramenta `read_working_memory` antes de escrever ou modificar código, "
            "para garantir que você tem o contexto atualizado. O Arquiteto rejeitará seu código se não fizer isso. "
            "Sempre salve o código gerado usando `save_code_to_rag` e atualize o progresso "
            "com `update_sprint_state`. Responda com TERMINATE quando a tarefa estiver concluída. "
            "[CRITICAL] NUNCA escreva blocos de código JSON simulando a chamada de ferramentas no seu texto. "
            "Sempre utilize o mecanismo NATIVO de Function Calling da API para acionar ferramentas."
        )
    )

    # Critério de parada: máximo de 10 turnos para evitar loops infinitos
    termination = MaxMessageTermination(max_messages=10)

    team = RoundRobinGroupChat(
        participants=[architect, engineer],
        termination_condition=termination
    )

    return team, architect, engineer


async def dummy_pubsub_listener():
    """Listener em background (Placeholder para a integração total no futuro)"""
    while True:
        await asyncio.sleep(60)

async def run_vitalia(task: str):
    """Executa uma tarefa no orquestrador Vitalia Cross-WSL."""
    team, _, _ = build_orchestrator()
    print(f"🚀 Orquestrador Vitalia iniciado. Tarefa: {task}")
    
    # Inicia a Task Assíncrona do Pub/Sub se ativada
    if os.getenv("VITALIA_PUBSUB_ENABLED", "False").lower() == "true":
        asyncio.create_task(dummy_pubsub_listener())
        
    from logger import logger
    
    async def log_and_yield(stream):
        async for message in stream:
            source = getattr(message, "source", "unknown")
            msg_type_name = type(message).__name__
            
            # Extrair uso de tokens se disponível
            usage = getattr(message, "models_usage", None)
            if usage:
                logger.log_event("telemetry", source, {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage, "completion_tokens", 0)
                })

            if msg_type_name == "TextMessage":
                logger.log_event("conversation", source, {"text": message.content})
            elif msg_type_name == "ToolCallRequestEvent":
                # Convert FunctionCall array to dict representation
                calls = [{"name": c.name, "arguments": c.arguments} for c in message.content] if isinstance(message.content, list) else str(message.content)
                logger.log_event("tool_call", source, {"request": calls})
            elif msg_type_name == "ToolCallExecutionEvent":
                results = [{"name": r.name, "content": r.content} for r in message.content] if isinstance(message.content, list) else str(message.content)
                logger.log_event("tool_call", source, {"execution_result": results})
            else:
                content = getattr(message, "content", "")
                logger.log_event("system_log", source, {"event_class": msg_type_name, "content": str(content)})
                
            yield message
            
    result = await Console(log_and_yield(team.run_stream(task=task)))
    return result

if __name__ == "__main__":
    asyncio.run(run_vitalia("Implemente uma função Python para calcular o IMC e salve no RAG."))
    import sys
    sys.exit(0)
