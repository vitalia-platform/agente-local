<!-- MANUAL-REFERENCIA.md | Atualizado em: 01-07-2026 15:03:06(GMT-04:00) -->
# Vitalia Agente Local — Manual de Referência Técnica

> **Audiência:** André (futuro-você) e colaboradores com domínio de Python/asyncio, Docker, Redis e LLMs.
> Sem tutoriais básicos. Foco em *por que* e *armadilhas*.

---

## Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Topologia de Hardware](#2-topologia-de-hardware)
3. [Decisões de Design (ADRs)](#3-decisões-de-design-adrs)
4. [Referência de Configuração (.env)](#4-referência-de-configuração-env)
5. [Pipeline E2E — Fases A–F](#5-pipeline-e2e--fases-af)
6. [Troubleshooting & Diagnóstico](#6-troubleshooting--diagnóstico)

---

## 1. Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        run_vitalia(task)                        │
│                                                                 │
│   build_orchestrator()                                          │
│   ┌──────────────┐          ┌──────────────┐                   │
│   │  Arquiteto   │          │  Engenheiro  │                   │
│   │  (Nó 1/CPU)  │          │  (Nó 2/GPU)  │                   │
│   │  NATIVE=false│          │  NATIVE=true │                   │
│   └──────┬───────┘          └──────┬───────┘                   │
│          │                         │                           │
│   VitaliaOllamaClient        OllamaChatCompletionClient        │
│   (Tool Bridge)              (Tool Calling nativo)             │
│          │                                                      │
│   ┌──────▼──────────────────────────────┐                      │
│   │         Redis Streams               │                      │
│   │  vitalia:tool_requests:Architect    │◄── tool_worker()     │
│   │  vitalia:tool_results:Architect     │──► asyncio.Task      │
│   └─────────────────────────────────────┘                      │
│                                                                 │
│   vitalia_events ──► telemetry_api.py ──► WebSocket ──► UI     │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes críticos

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| `build_orchestrator()` | `main.py` | Monta Arquiteto + Engenheiro com clientes corretos conforme `.env` |
| `VitaliaOllamaClient` | `main.py` | Intercepta JSON cru de tool call, media via Redis Streams |
| `tool_worker()` | `main.py` | `asyncio.Task` que executa ferramentas localmente via `TOOL_REGISTRY` |
| `run_vitalia()` | `main.py` | Entry point: cria conexões Redis, lança worker, inicia AutoGen loop |
| `telemetry_api.py` | `vitalia-core/` | FastAPI: WebSocket bridge para o Dashboard, auth JWT, controle Docker |
| `logger.py` | `vitalia-core/` | EventLogger: publica em `vitalia_events` + persiste em shards `.jsonl` |
| `tools.py` | `vitalia-core/` | Ferramentas: `web_search`, `save_code_to_rag`, `update_sprint_state`, etc. |

---

## 2. Topologia de Hardware

| Nó | Máquina | Modelo | `TOOL_CALLING_NATIVE` | Cliente |
|---|---|---|---|---|
| Nó 1 | Notebook (CPU/Swap) | `llama3.2:3b` | `false` | `VitaliaOllamaClient` (Bridge) |
| Nó 2 | Servidor (GTX 1060 6GB) | `qwen2.5-coder:7b` | `true` | `OllamaChatCompletionClient` |

> [!NOTE]
> **Por que dois clientes diferentes?** O `llama3.2:3b` rodando em CPU no Nó 1 não emite `tool_call` no formato esperado pela API do Ollama — ele vaza um JSON cru como texto puro no campo `content`. O `VitaliaOllamaClient` intercepta esse JSON *dentro do `.create()`*, antes que o AutoGen veja a resposta, e converte para `FunctionCall`. O Nó 2 com GPU emite o formato correto nativamente.

> [!IMPORTANT]
> **Upgrade de hardware:** Para usar tool calling nativo no Nó 1 (ex: nova GPU com 8GB+ VRAM), basta setar `NO1_TOOL_CALLING_NATIVE=true` no `.env`. Zero código alterado — esse é o invariante arquitetural central desta refatoração.

---

## 3. Decisões de Design (ADRs)

### ADR-01 — Tool Bridge via Redis Streams (não via callback direto)

**Problema:** AutoGen roteia a resposta do LLM *antes* que possamos injetar o resultado da ferramenta no mesmo turno.

**Decisão:** O wrapper `VitaliaOllamaClient.create()` detecta o JSON, posta em `vitalia:tool_requests:<agent>`, aguarda com `asyncio.Event` e retorna `FunctionCall` ao AutoGen — como se o tool call tivesse sido nativo.

**Trade-off aceito:** Latência de 1 round-trip Redis (~1ms local) por tool call. Aceitável dado que a inferência do LLM já leva segundos.

**Alternativa rejeitada:** Patch de monkey-patch no AutoGen — frágil a atualizações de versão.

### ADR-02 — `correlation_id` (UUID4) por pedido

**Problema:** Múltiplos tool calls em paralelo poderiam cruzar respostas na stream.

**Decisão:** Cada pedido gera um UUID4. O `tool_worker()` posta o resultado com o mesmo `correlation_id`. O wrapper filtra por ele no XREAD.

**Armadilha conhecida:** Se o worker crashar após o XADD de request mas antes do XADD de result, o wrapper ficará bloqueado até o `TOOL_BRIDGE_TIMEOUT_SEC`. O resultado é uma mensagem de erro descritiva ao LLM, não um crash do sistema.

### ADR-03 — `HeadAndTailChatCompletionContext` no Engenheiro

**Problema:** O `qwen2.5-coder:7b` com 6GB de VRAM não aguenta contexto longo. Com head=1 e tail=20, o Engenheiro sempre vê a tarefa inicial (head) e as últimas 20 mensagens (tail).

**Armadilha:** Se o Engenheiro estiver "confuso" e repetindo respostas, verifique se `tail_size=20` é suficiente para o contexto da sprint. Aumente para 30 se necessário, mas monitore a VRAM.

### ADR-04 — Sem retry automático no Tool Bridge

**Decisão deliberada:** Timeout → erro descritivo legível pelo LLM, que pode decidir tentar novamente ou reportar o problema. Retry automático mascararia falhas sistêmicas (Redis down, worker crash).

---

## 4. Referência de Configuração (.env)

### 4.1 Infraestrutura

| Variável | Padrão | Descrição |
|---|---|---|
| `POSTGRES_DB` | `vitalia_db` | Nome do banco pgvector |
| `POSTGRES_USER` | `vitalia_admin` | Usuário do banco |
| `POSTGRES_PASSWORD` | — | Senha do banco (nunca commitar) |
| `POSTGRES_PORT` | `5432` | Porta exposta |
| `DB_CONTAINER_NAME` | `vitalia_db` | Nome do container Docker |
| `REDIS_CONTAINER_NAME` | `vitalia_redis` | Nome do container Redis |
| `REDIS_PORT` | `6379` | Porta exposta |
| `REDIS_PASSWORD` | — | Senha do Redis (nunca commitar) |
| `OLLAMA_CONTAINER_NAME` | `vitalia_ollama` | Container Ollama local |
| `WEBUI_CONTAINER_NAME` | `vitalia_open_webui` | Container Open WebUI |
| `DASHBOARD_SECRET_KEY` | — | Chave JWT do Dashboard (nunca commitar) |

### 4.2 Rede Cross-WSL

| Variável | Exemplo | Descrição |
|---|---|---|
| `NO1_LOCAL_OLLAMA_URL` | `http://localhost:11434/v1` | URL do Ollama no Nó 1 |
| `NO2_SERVER_IP` | `http://192.168.0.218:11434/v1` | URL do Ollama no Nó 2 |
| `NO2_OLLAMA_PORT` | `11434` | Porta Ollama no servidor |
| `VITALIA_PUBSUB_ENABLED` | `True` | Habilita Redis PubSub para eventos |
| `NODE_TYPE` | `notebook` | Identifica a máquina (`notebook` ou `server`) |

### 4.3 Perfis de Hardware (crítico — leia o ADR-01)

| Variável | Tipo | Descrição |
|---|---|---|
| `NO1_MODEL` | string | Modelo a carregar no Nó 1 (ex: `llama3.2:3b`) |
| `NO2_MODEL` | string | Modelo a carregar no Nó 2 (ex: `qwen2.5-coder:7b`) |
| `NO1_TOOL_CALLING_NATIVE` | `true`/`false` | Se `false`: usa `VitaliaOllamaClient` (Bridge) |
| `NO2_TOOL_CALLING_NATIVE` | `true`/`false` | Se `false`: usa `VitaliaOllamaClient` (Bridge) |
| `TOOL_BRIDGE_TIMEOUT_SEC` | `30` | Timeout em segundos para o Bridge aguardar o worker |

> [!CAUTION]
> **`NO1_MODEL` e `NO2_MODEL` são obrigatórias.** Se ausentes, `build_orchestrator()` passa `None` para o cliente Ollama e falha silenciosamente na primeira inferência, não na inicialização.

### 4.4 Perfis de Roteamento (legado — não usados no orquestrador atual)

| Variável | Descrição |
|---|---|
| `ROUTER_LLM_PROFILE` | Perfil para o agente roteador (não implementado no orquestrador atual) |
| `DEVELOPER_LLM_PROFILE` | Perfil para o agente desenvolvedor |
| `INFRA_LLM_PROFILE` | Perfil para o agente de infra |
| `REVIEW_LLM_PROFILE` | Perfil para o agente revisor |

> [!NOTE]
> Essas variáveis existem no `.env` por compatibilidade com versões anteriores e com o Benchmark Runner do Dashboard, que permite atribuir modelos a perfis via UI. O orquestrador atual usa `NO1_MODEL`/`NO2_MODEL` diretamente.

### 4.5 APIs Cloud (opcionais)

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave Google Gemini (deixar vazio se não usar) |
| `ANTHROPIC_API_KEY` | Chave Anthropic Claude |
| `OPENAI_API_KEY` | Chave OpenAI |

---

## 5. Pipeline E2E — Fases A–F

**Pré-requisito:** `cd /home/andre/projetos/assistidos/agente-local && source .venv/bin/activate`

### Fase A — Infraestrutura

```bash
# A.0 — Containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

> [!NOTE]
> Esperado: 4 containers `Up` — `vitalia_redis`, `vitalia_db`, `vitalia_ollama`, `vitalia_open_webui`. Se algum estiver `Exited`, `docker-compose up -d` na raiz.

```bash
# A.1 — Redis
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 ping
# Warning de senha é esperado e inofensivo — o que importa é o PONG
```

```bash
# A.2 — pgvector
docker exec -it vitalia_db psql -U vitalia_admin -d vitalia_db -c "SELECT 1;"
```

### Fase B — Conectividade Cross-WSL

```bash
# B.1 — Nó 1
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep '"name"' | head -5

# B.2 — Nó 2
curl -s http://192.168.0.218:11434/api/tags | python3 -m json.tool | grep '"name"' | head -5

# B.3 — Latência (aceitável < 100ms)
time curl -s http://192.168.0.218:11434/api/tags > /dev/null
```

> [!NOTE]
> **Se B.2 falhar:** O servidor pode estar com o Ollama escutando só em `localhost`. No servidor: `ollama serve` sem `--host` restringe à loopback. Corrija com `OLLAMA_HOST=0.0.0.0 ollama serve` ou via variável de ambiente no `docker-compose.yml` do servidor.

### Fase C — Perfil de Hardware

```bash
# C.1 — Confirmar variáveis críticas
grep -E "NO1_MODEL|NO2_MODEL|NO1_TOOL_CALLING_NATIVE|NO2_TOOL_CALLING_NATIVE|TOOL_BRIDGE_TIMEOUT_SEC|NO2_SERVER_IP" .env
```

```bash
# C.2 — Validar build_orchestrator()
cd vitalia-core && python3 - << 'EOF'
import os, sys
from dotenv import load_dotenv
load_dotenv("../.env")
sys.path.insert(0, ".")
from unittest.mock import patch, MagicMock
with patch("main.build_ollama_client", return_value=MagicMock()):
    from main import build_orchestrator
    team, architect, engineer = build_orchestrator()
    native_no1 = os.getenv("NO1_TOOL_CALLING_NATIVE", "false").lower() == "true"
    arch_tools = architect._tools if hasattr(architect, "_tools") else []
    print(f"NO1_MODEL        : {os.getenv('NO1_MODEL')}")
    print(f"NO2_MODEL        : {os.getenv('NO2_MODEL')}")
    print(f"NO1_TOOL_NATIVE  : {os.getenv('NO1_TOOL_CALLING_NATIVE')}")
    print(f"NO2_TOOL_NATIVE  : {os.getenv('NO2_TOOL_CALLING_NATIVE')}")
    print(f"Architect tools  : {len(arch_tools)}")
    print(f"Engineer context : {type(engineer._model_context).__name__}")
    print("✅ build_orchestrator() OK")
EOF
```

### Fase D — Testes Unitários

```bash
cd /home/andre/projetos/assistidos/agente-local
.venv/bin/python -m pytest vitalia-core/tests/ -v --tb=short
# Esperado: 9 passed (6 test_main_e2e + 3 test_tools)
```

### Fase E — Tool Bridge Isolado (sem Ollama)

```bash
cd vitalia-core && ../.venv/bin/python3 - << 'EOF'
import asyncio, os
from dotenv import load_dotenv
load_dotenv("../.env")
import redis.asyncio as redis_async

REDIS_URL = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:{os.getenv('REDIS_PORT', 6379)}/0"

async def test_bridge_channel():
    r = redis_async.Redis.from_url(REDIS_URL)
    cid = "bench-test-001"
    stream_req = "vitalia:tool_requests:Architect"
    stream_res = "vitalia:tool_results:Architect"
    try:
        await r.delete(stream_req, stream_res)
    except Exception:
        pass
    await r.xadd(stream_req, {"correlation_id": cid, "tool_name": "web_search",
        "arguments_json": '{"query": "vitalia bench test"}', "agent_name": "Architect",
        "timestamp": "2026-06-30T20:00:00"})
    print(f"✅ XADD em {stream_req} OK")
    await r.xadd(stream_res, {"correlation_id": cid, "result": "Resultado simulado",
        "error": "", "duration_ms": "50"})
    print(f"✅ XADD em {stream_res} OK")
    messages = await r.xread(streams={stream_res: "0"}, count=10, block=1000)
    found = any(
        fields.get(b"correlation_id", b"").decode() == cid
        for _, msgs in messages for _, fields in msgs
    )
    print("✅ XREAD resultado OK" if found else "❌ Resultado não encontrado")
    await r.aclose()
    print("✅ Tool Bridge Channel: PASS")

asyncio.run(test_bridge_channel())
EOF
```

### Fase F — Inferência End-to-End

> [!CAUTION]
> Consome VRAM do Nó 2. Demora 1–5 min. Rode só após A–E passarem.

```bash
cd vitalia-core && ../.venv/bin/python3 - << 'EOF'
import asyncio, sys
sys.path.insert(0, ".")
from main import run_vitalia

asyncio.run(run_vitalia("""
[BENCH TEST 30-06-2026]
1. Arquiteto: use web_search para buscar 'Python asyncio best practices 2024' e cite 1 resultado.
2. Engenheiro: escreva uma função Python de 3 linhas com asyncio.gather() e salve no RAG.
3. Ao concluir, responda com TERMINATE.
"""))
EOF
```

```bash
# F.3 — Verificar streams após o ciclo
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XRANGE vitalia:tool_requests:Architect - + COUNT 5
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XRANGE vitalia:tool_results:Architect - + COUNT 5
```

---

## 6. Troubleshooting & Diagnóstico

### Redis

```bash
# Ver todas as streams ativas
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 KEYS "vitalia:*"

# Últimos 50 eventos de auditoria
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XREVRANGE vitalia:events + - COUNT 50

# Reset completo de streams de teste
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  DEL vitalia:tool_requests:Architect vitalia:tool_results:Architect

# Flush total (cuidado em produção)
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 FLUSHDB
```

### VRAM (Nó 2)

```bash
# No servidor
nvidia-smi --query-gpu=name,memory.used,memory.free,memory.total --format=csv
# qwen2.5-coder:7b ocupa ~5.5GB dos 6GB. Se usado_mb > 5800, reinicie o Ollama.
docker restart vitalia_ollama
```

### Armadilhas conhecidas

| Sintoma | Causa | Solução |
|---|---|---|
| `NO1_MODEL: None` na Fase C | Variável ausente do `.env` | Adicionar `NO1_MODEL=llama3.2:3b` |
| Tool call como `TextMessage` ao invés de `ToolCallRequestEvent` | LLM não retornou JSON `{name, arguments}` | Verificar system_message do Arquiteto; o LLM pode ter "esquecido" o formato |
| Worker timeout após `TOOL_BRIDGE_TIMEOUT_SEC` | Redis inacessível ou `tool_worker()` não foi lançado | Verificar se `NATIVE=false` em algum nó (worker só é lançado neste caso) |
| `ConnectionRefusedError` no Redis | Container parado ou senha errada | `docker restart vitalia_redis` e conferir `REDIS_PASSWORD` |
| VRAM OOM no Nó 2 | Outro processo ocupando a GPU | `nvidia-smi` para identificar; `docker restart vitalia_ollama` para liberar |
| `asyncio.CancelledError` no log | Normal — o `tool_worker()` usa isso para encerrar o loop | Ignorar se aparecer apenas no shutdown |
| Dashboard JWT expirado | Token de 60min expirou | Fazer logout e re-autenticar no Dashboard |

### Dashboard

```bash
# Iniciar o Control Plane
cd vitalia-core
../.venv/bin/uvicorn telemetry_api:app --host 0.0.0.0 --port 8000 --reload

# Acessar: http://localhost:8000
# Senha: valor de DASHBOARD_SECRET_KEY no .env
```

---

*Vitalia Agente Local | Manual de Referência Técnica | 30-06-2026*
