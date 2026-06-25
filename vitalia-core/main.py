# <!-- main.py | Atualizado em: 24-06-2026 18:20:00(GMT-04:00) -->
import os
import asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.ui import Console

from tools import save_code_to_rag, update_sprint_state, web_search, read_working_memory, query_audit_log

# Configurações lidas do .env (Zero Hardcoding - Art. VI)
NO1_URL = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434/v1")
NO2_URL = os.getenv("NO2_SERVER_IP", "http://server-ip:11434/v1")


def build_ollama_client(base_url: str, model: str) -> OpenAIChatCompletionClient:
    """Constrói um cliente Ollama (API OpenAI-compatible) para um nó específico."""
    return OpenAIChatCompletionClient(
        model=model,
        base_url=base_url,
        api_key="ollama",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "structured_output": False,
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
            "Responda com TERMINATE quando o objetivo da sprint estiver concluído."
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
            "com `update_sprint_state`. Responda com TERMINATE quando a tarefa estiver concluída."
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
        
    result = await Console(team.run_stream(task=task))
    return result

if __name__ == "__main__":
    asyncio.run(run_vitalia("Implemente uma função Python para calcular o IMC e salve no RAG."))
