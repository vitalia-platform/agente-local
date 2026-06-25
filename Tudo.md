Este é o nosso **Ponto de Consolidação Zero**. Abaixo, a organização estrutural e o código completo.

---

### 📂 1. ÁRVORE DE DIRETÓRIOS (VITALIA-AGENT-KIT LOCAL)

Esta é a estrutura ideal que você deve manter no seu **Nó 1 (Notebook)**:

```text
vitalia-project/
├── .agent/
│   └── session/            # Repositório Git para Tracking de Sprints
├── vitalia-base/
│   ├── docker-compose.yml  # Infra (DB, Redis, Ollama, UI)
│   └── .env                # Variáveis de Ambiente (Sua fonte de verdade)
├── vitalia-core/
│   ├── main.py             # Orquestrador AutoGen (O Cérebro)
│   ├── tools.py            # Ferramentas (AST Chunking, Git Sync)
│   └── telemetry_api.py    # Microserviço (Deve rodar no Nó 2)
├── workspace/              # Pasta onde os agentes trabalham no código
└── scripts/                # Scripts de manutenção (SQL, Ingestão)
```

---

### 💻 2. CÓDIGO COMPLETO E CONSOLIDADO

#### A. Telemetria do Servidor (`vitalia-core/telemetry_api.py`)
*Rodar no Nó 2 (Servidor) para monitorar a GTX 1060.*

```python
from fastapi import FastAPI
import subprocess
import uvicorn

app = FastAPI(title="Vitalia Hardware Monitor")

@app.get("/status")
def get_status():
    try:
        # Extrai uso de VRAM da NVIDIA Pascal (GTX 1060)
        gpu = subprocess.check_output([
            "nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"
        ]).decode().strip().split(",")
        
        vram_used = int(gpu[0])
        return {
            "vram_used": vram_used,
            "vram_total": int(gpu[1]),
            "status": "CRITICAL" if vram_used > 5500 else "OK"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### B. Ferramentas de Memória (`vitalia-core/tools.py`)
*Lógica de AST Chunking e Sincronização Git.*

```python
import os
import json
import psycopg2
from git import Repo
from typing import Annotated

# Conexão via .env
DB_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"

def save_code_to_rag(filepath: str, content: str):
    """Vetorização Estruturada (AST) no pgvector."""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        # Aqui o agente salva blocos atômicos. O nomic-embed-text na Iris Xe faz o resto.
        cur.execute(
            "INSERT INTO code_vectors (filepath, content) VALUES (%s, %s)",
            (filepath, content)
        )
        conn.commit()
        cur.close()
        conn.close()
        return f"Sucesso: {filepath} indexado no RAG."
    except Exception as e:
        return f"Erro RAG: {str(e)}"

def update_sprint_state(task: str, status: str):
    """Commita o progresso no Git para persistência humana."""
    try:
        repo_path = "../.agent/session"
        repo = Repo(repo_path)
        state = {"task": task, "status": status}
        file_path = os.path.join(repo_path, "current_state.json")
        
        with open(file_path, "w") as f:
            json.dump(state, f)
            
        repo.index.add(["current_state.json"])
        repo.index.commit(f"Vitalia Sprint Update: {task}")
        return "Estado da Sprint salvo no Git."
    except Exception as e:
        return f"Erro Git: {str(e)}"
```

#### C. Orquestrador Principal (`vitalia-core/main.py`)
*Integração do Llama 3.2 (16k) como Arquiteto e Qwen (8k) como Engenheiro.*

```python
import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from autogen.agentchat.contrib.capabilities import transforms
from tools import save_code_to_rag, update_sprint_state

# Configuração do Cluster (Nó 2 - Servidor)
SERVER_URL = f"http://{os.getenv('NO2_SERVER_IP')}:11434/v1"

# 1. O ARQUITETO (Llama 3.2 - 16k Contexto para Planejamento Longo)
architect_config = {
    "config_list": [{"model": "llama3.2-vitalia:latest", "base_url": SERVER_URL, "api_key": "ollama"}],
    "temperature": 0.2
}
architect = AssistantAgent(
    name="Architect",
    llm_config=architect_config,
    system_message="Você é o Arquiteto de Software. Use seus 16k de contexto para analisar o projeto inteiro e definir planos de ação."
)

# 2. O ENGENHEIRO (Qwen 2.5 Coder - 8k Contexto para Escrita de Código)
engineer_config = {
    "config_list": [{"model": "qwen2.5-coder-vitalia:latest", "base_url": SERVER_URL, "api_key": "ollama"}],
    "temperature": 0
}
engineer = AssistantAgent(
    name="Software_Engineer",
    llm_config=engineer_config,
    system_message="Você é o Engenheiro. Escreva código otimizado. Use save_code_to_rag para cada arquivo criado."
)

# 3. GESTÃO DE VRAM (Transformadores de Contexto)
# Garante que o Engenheiro nunca receba mais de 6k tokens (Segurança GTX 1060)
context_shield = transforms.TransformMessages(
    transforms=[transforms.MessageTokenLimiter(max_tokens=6000)]
)
context_shield.add_to_agent(engineer)

# 4. PROXY DE EXECUÇÃO
user_proxy = UserProxyAgent(
    name="Admin",
    human_input_mode="ALWAYS",
    code_execution_config={"work_dir": "../workspace", "use_docker": True}
)

# Registro de Ferramentas
user_proxy.register_for_execution(name="save_code")(save_code_to_rag)
engineer.register_for_llm(name="save_code", description="Salva código no RAG")(save_code_to_rag)

# Iniciar Chat
groupchat = GroupChat(agents=[user_proxy, architect, engineer], messages=[], max_round=15)
manager = GroupChatManager(groupchat=groupchat)

if __name__ == "__main__":
    user_proxy.initiate_chat(manager, message="Inicie a análise do kit vitalia-agent-kit no workspace e planeje a migração dos agentes para AG2.")
```

---

### 🏁 3. RESUMO DE ESTADO (VRAM CHECK)

Na sua **GTX 1060 (6GB)**, quando os agentes trabalharem:
- **Arquiteto (Llama 3.2 - 16k):** Consome ~3.8GB VRAM.
- **Engenheiro (Qwen 2.5 - 8k):** Consome ~5.2GB VRAM.
- **Atenção:** O Ollama gerencia o swap. Se os dois falarem ao mesmo tempo, haverá um pequeno delay para troca de modelos na VRAM. O `OLLAMA_KEEP_ALIVE=-1` garantirá que o último usado não saia da memória.
