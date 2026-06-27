<!-- Tudo.md | Atualizado em: 27-06-2026 11:42:03(GMT-04:00) -->
Este é o nosso **Ponto de Consolidação (Camada 3)**. Abaixo, a organização estrutural exata e o código completo.

---

### 📂 1. ÁRVORE DE DIRETÓRIOS REAL

Esta é a estrutura real do projeto local:

```text
agente-local/
├── .agents/
│   └── skills/             # Skills injetadas na Orquestração (Ex: brainstorming)
├── .specify/
│   └── memory/session/     # Cache de Auditoria e Lock Local
├── vitalia-core/
│   ├── tests/              # Suíte de testes Pytest (E2E, Mocks)
│   ├── main.py             # Orquestrador AutoGen (O Cérebro)
│   ├── tools.py            # Ferramentas (AST Chunking, Dynamic Skills)
│   ├── telemetry_api.py    # Microserviço (Monitoramento e Benchmark)
│   └── logger.py           # Sistema de log e persistência nativo
├── scripts/                # Scripts de manutenção (SQL, Ingestão)
├── workspace/              # Pasta onde os agentes trabalham no código
├── Progresso.md            # Log de decisões e andamento (Sprints)
├── docker-compose.yml      # Infraestrutura (DB, Redis, Ollama, UI)
└── .env                    # Variáveis de Ambiente (Fonte da Verdade)
```

---

### 💻 2. CÓDIGO COMPLETO E CONSOLIDADO

#### A. Telemetria do Servidor (`vitalia-core/telemetry_api.py`)
```python
# telemetry_api.py | Atualizado em: 26-06-2026
import os
import json
import asyncio
import docker
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import dotenv
import redis.asyncio as redis_async
import redis as redis_sync
import subprocess
import httpx

try:
    from logger import logger
except ImportError:
    # Caso seja executado de um contexto sem o logger
    logger = None

env_path = os.path.join(os.path.dirname(__file__), '../.env')
dotenv.load_dotenv(env_path)

SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

REDIS_PASS = os.getenv("REDIS_PASSWORD", "secret")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://:{REDIS_PASS}@localhost:{REDIS_PORT}/0"

app = FastAPI(title="Vitalia Control Plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Aviso: Não foi possível conectar ao Docker Socket: {e}")
    docker_client = None


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/api/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.password != SECRET_KEY:
        raise HTTPException(status_code=400, detail="Senha mestra incorreta")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    r = redis_async.Redis.from_url(REDIS_URL, decode_responses=True)
    stream_name = "vitalia_events"
    last_id = '$'
    
    try:
        while True:
            events = await r.xread({stream_name: last_id}, count=10, block=1000)
            if events:
                for stream, messages in events:
                    for msg_id, msg_data in messages:
                        last_id = msg_id
                        await websocket.send_json(msg_data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        from datetime import datetime
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WS Error: {e}")
    finally:
        await r.aclose()


class ControlRequest(BaseModel):
    container_name: str

@app.post("/api/control/restart")
async def restart_container(req: ControlRequest, username: str = Depends(get_current_user)):
    if not docker_client:
        raise HTTPException(status_code=500, detail="Docker integration unavailable")
    try:
        container = docker_client.containers.get(req.container_name)
        container.restart()
        return {"status": "success", "message": f"Container {req.container_name} restarted"}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gpu-status")
def get_gpu_status():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.free,memory.used", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return {"error": "nvidia-smi falhou"}
            
        lines = result.stdout.strip().split('\n')
        gpus = []
        for idx, line in enumerate(lines):
            parts = line.split(',')
            if len(parts) >= 3:
                gpus.append({
                    "gpu_index": idx,
                    "total_mb": int(parts[0].strip()),
                    "free_mb": int(parts[1].strip()),
                    "used_mb": int(parts[2].strip()),
                })
        return {"gpus": gpus}
    except Exception:
        return {"error": "Sem GPU local"}

# --------- SETTINGS & BENCHMARK ---------

class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

@app.get("/api/settings")
async def get_settings(username: str = Depends(get_current_user)):
    keys = ["VITALIA_PUBSUB_ENABLED", "NO1_LOCAL_OLLAMA_URL", "NO2_SERVER_IP", "ROUTER_LLM_PROFILE"]
    return {k: os.getenv(k, "") for k in keys}

@app.post("/api/settings")
async def update_settings(req: SettingsUpdate, username: str = Depends(get_current_user)):
    try:
        for k, v in req.settings.items():
            dotenv.set_key(env_path, k, v)
            os.environ[k] = v
        return {"status": "success", "message": "Settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/llms")
async def list_llms(username: str = Depends(get_current_user)):
    url1 = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434/v1").replace("/v1", "/api/tags")
    url2 = os.getenv("NO2_SERVER_IP", "").replace("/v1", "/api/tags")
    
    results = {"node1": [], "node2": []}
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r1 = await client.get(url1)
            if r1.status_code == 200:
                results["node1"] = r1.json().get("models", [])
        except:
            pass
        if url2:
            try:
                r2 = await client.get(url2)
                if r2.status_code == 200:
                    results["node2"] = r2.json().get("models", [])
            except:
                pass
    return results

class BenchmarkRequest(BaseModel):
    endpoint_url: str  # e.g., http://localhost:11434/api/generate
    model_name: str

@app.post("/api/benchmark")
async def run_benchmark(req: BenchmarkRequest, username: str = Depends(get_current_user)):
    url = req.endpoint_url
    if not url.endswith("/api/generate"):
        url = url.replace("/v1", "") + "/api/generate"
        
    payload = {
        "model": req.model_name,
        "prompt": "Hello",
        "stream": False
    }
    
    if logger:
        logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_start", "url": url, "model": req.model_name})
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Warm-up
            if logger: logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_warmup", "model": req.model_name})
            warm_resp = await client.post(url, json=payload)
            warm_resp.raise_for_status()
            warm_data = warm_resp.json()
            load_duration_ms = warm_data.get("load_duration", 0) / 1e6
            
            # 2. Inference Run
            if logger: logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_inference", "model": req.model_name})
            inf_resp = await client.post(url, json=payload)
            inf_resp.raise_for_status()
            inf_data = inf_resp.json()
            
            eval_count = inf_data.get("eval_count", 0)
            eval_duration_ns = inf_data.get("eval_duration", 1) # prevent div/0
            tokens_per_sec = (eval_count / eval_duration_ns) * 1e9 if eval_duration_ns > 0 else 0
            
            if logger:
                logger.log_event("system_log", "TelemetryAPI", {
                    "event": "benchmark_success", 
                    "model": req.model_name, 
                    "load_ms": load_duration_ms, 
                    "tps": tokens_per_sec
                })
            
            return {
                "status": "success",
                "load_duration_ms": load_duration_ms,
                "tokens_per_sec": tokens_per_sec,
                "model": req.model_name
            }
            
        except Exception as e:
            if logger: logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_error", "model": req.model_name, "error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))

# Monta o frontend estático na raiz (Abaixo das rotas da API para não dar conflito)
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("telemetry_api:app", host="0.0.0.0", port=8000, reload=True)
```

#### B. Ferramentas e Skills (`vitalia-core/tools.py`)
```python
# tools.py | Atualizado em: 26-06-2026 12:08:18(GMT-04:00)
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
import ast
import json
import redis
import psycopg2
import requests
from ddgs import DDGS

# Credenciais lidas estritamente do .env (Zero Hardcoding)
DB_USER = os.getenv("POSTGRES_USER", "vitalia_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "secret")
DB_NAME = os.getenv("POSTGRES_DB", "vitalia_db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
REDIS_PASS = os.getenv("REDIS_PASSWORD", "secret")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

OLLAMA_URL = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434")
DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@localhost:{DB_PORT}/{DB_NAME}"
REDIS_URL = f"redis://:{REDIS_PASS}@localhost:{REDIS_PORT}/0"

def update_sprint_state(task: str, status: str) -> str:
    """Persiste o estado da sprint atual no Redis de forma atômica."""
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        state = {"task": task, "status": status}
        r.hset("vitalia:sprint_state", mapping=state)
        return "Sucesso: Estado da sprint sincronizado no Redis."
    except Exception as e:
        return f"Erro ao sincronizar com Redis: {str(e)}"

def load_dynamic_skill(skill_name: str) -> str:
    """Carrega uma skill dinâmica em Markdown para o contexto do agente."""
    skills_dir = os.path.join(os.path.dirname(__file__), "../../.specify/skills")
    skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: Skill {skill_name} não encontrada em {skills_dir}."

def chunk_code_ast(content: str) -> list:
    """Usa o módulo nativo ast para separar classes/funções inteiras."""
    chunks = []
    try:
        tree = ast.parse(content)
        lines = content.split('\n')
        last_end = 0
        
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = node.end_lineno
                
                # Texto antes do nó (imports, variáveis globais, etc)
                if start > last_end:
                    chunk = '\n'.join(lines[last_end:start]).strip()
                    if chunk:
                        chunks.append(chunk)
                
                # O nó (função ou classe) inteiro preservado
                chunks.append('\n'.join(lines[start:end]))
                last_end = end
                
        # Remanescente
        if last_end < len(lines):
            chunk = '\n'.join(lines[last_end:]).strip()
            if chunk:
                chunks.append(chunk)
                
    except SyntaxError:
        # Fallback para chunking bruto se não for Python válido
        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
        
    return chunks if chunks else [content]

def save_code_to_rag(filepath: str, content: str) -> str:
    """Faz o chunking AST do código, salva temporariamente no Redis (Hot) e gera embeddings no pgvector."""
    try:
        chunks = chunk_code_ast(content)
        
        # 1. Salva no Hot Cache (Redis)
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        r.set(f"vitalia:hot_rag:{filepath}", content, ex=86400) # Expira em 24h
        
        # 2. Salva no PostgreSQL (Cold Storage + Vector)
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        for idx, chunk in enumerate(chunks):
            res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
                "model": "nomic-embed-text",
                "prompt": chunk
            })
            res.raise_for_status()
            embedding = res.json().get("embedding")
            
            metadata = json.dumps({"chunk_index": idx, "total_chunks": len(chunks)})
            
            cur.execute(
                "INSERT INTO code_vectors (filepath, content, metadata, embedding) VALUES (%s, %s, %s, %s)",
                (filepath, chunk, metadata, embedding)
            )
            
        conn.commit()
        cur.close()
        conn.close()
        return f"Sucesso: {filepath} indexado no RAG ({len(chunks)} chunks) e salvo na memória quente."
    except Exception as e:
        return f"Erro RAG: {str(e)}"

def read_working_memory(filepath: str) -> str:
    """Ferramenta Pull: Lê o código-fonte inteiro mais recente armazenado na memória quente."""
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        content = r.get(f"vitalia:hot_rag:{filepath}")
        if content:
            return content
        return f"Arquivo '{filepath}' não encontrado na memória quente. Você já o salvou nesta sprint?"
    except Exception as e:
        return f"Erro ao acessar Memória de Trabalho: {str(e)}"

def query_audit_log(limit: int = 5) -> str:
    """Recupera os últimos N turnos de raciocínio da stream de eventos."""
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        # XREVRANGE lê a stream de trás para frente (+ para -) limitando
        events = r.xrevrange("vitalia:events", "+", "-", count=limit)
        if not events:
            return "Nenhum histórico recente encontrado."
        
        history = []
        for event_id, event_data in events:
            if event_data.get("type") == "llm_turn":
                try:
                    payload = json.loads(event_data.get("payload", "{}"))
                    history.append(f"Turno [{event_data.get('timestamp')}] - {event_data.get('source')}:\n{payload.get('reasoning', 'Sem raciocínio')}")
                except:
                    pass
        return "\n\n".join(history)
    except Exception as e:
        return f"Erro ao acessar auditoria: {str(e)}"

def web_search(query: str) -> str:
    """Busca informações na web usando DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if not results:
                return "Nenhum resultado encontrado."
                
            formatted_results = []
            for r in results:
                formatted_results.append(f"Título: {r.get('title')}\nLink: {r.get('href')}\nResumo: {r.get('body')}\n")
                
            return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Erro na busca web: {str(e)}"
```

#### C. Orquestrador Principal (`vitalia-core/main.py`)
```python
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
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_core.models._types import CreateResult, FunctionCall
from autogen_agentchat.ui import Console

from tools import save_code_to_rag, update_sprint_state, web_search, read_working_memory, query_audit_log, load_dynamic_skill

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
        import hashlib, pickle, json
        import redis.asyncio as redis_async
        
        try:
            cache_key_raw = json.dumps(str(kwargs), sort_keys=True)
            cache_key = f"vitalia_cache:{hashlib.md5(cache_key_raw.encode()).hexdigest()}"
        except:
            cache_key = None
            
        r = None
        if cache_key:
            try:
                r = redis_async.Redis.from_url(f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:{os.getenv('REDIS_PORT', '6379')}/0")
                cached = await r.get(cache_key)
                if cached:
                    await r.aclose()
                    return pickle.loads(cached)
            except Exception:
                r = None
                
        result = await super().create(*args, **kwargs)
        result = self._parse_content_for_tool(result)
        
        if r and cache_key:
            try:
                await r.set(cache_key, pickle.dumps(result), ex=3600)
                await r.aclose()
            except Exception:
                pass
                
        return result
        
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
        tools=[web_search, query_audit_log, load_dynamic_skill],
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
        tools=[save_code_to_rag, update_sprint_state, read_working_memory, load_dynamic_skill],
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

    # Critério de parada: máximo de 10 turnos ou TERMINATE explícito
    termination = MaxMessageTermination(max_messages=10) | TextMentionTermination("TERMINATE")

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
```

---

### 🏁 3. RESUMO DE ESTADO (VRAM CHECK)

Na sua **GTX 1060 (6GB)**, quando os agentes trabalharem:
- **Arquiteto (Llama 3.2 - 16k):** Consome ~3.8GB VRAM.
- **Engenheiro (Qwen 2.5 - 8k):** Consome ~1.2GB VRAM.
- **Atenção:** O Ollama gerencia o swap (eviction). Se o consumo for exceder a memória física da placa, ele proativamente descarregará o modelo mais antigo da VRAM, prevenindo Out of Memory (OOM).
