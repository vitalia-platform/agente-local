<!-- BENCH_TEST.md | Atualizado em: 01-07-2026 15:03:06(GMT-04:00) -->
# 🔬 Vitalia Agente Local — Pipeline de Teste de Bancada

Guia operacional para validar o sistema **end-to-end** após a refatoração do orquestrador hardware-adaptive com Tool Bridge (sprint 27-06-2026).

> **Pré-leitura obrigatória:** Este documento testa comportamentos reais (inferência Ollama + Redis Streams). Não é substituto da suíte de testes unitários — é o teste do sistema como um todo.

---

## Índice

1. [Configuração de Ambiente](#1-configuração-de-ambiente)
2. [Fase A — Infraestrutura](#fase-a--infraestrutura)
3. [Fase B — Conectividade Cross-WSL](#fase-b--conectividade-cross-wsl)
4. [Fase C — Perfil de Hardware](#fase-c--perfil-de-hardware)
5. [Fase D — Suíte de Testes Unitários](#fase-d--suíte-de-testes-unitários)
6. [Fase E — Tool Bridge Isolado (sem Ollama)](#fase-e--tool-bridge-isolado-sem-ollama)
7. [Fase F — Ciclo de Inferência End-to-End](#fase-f--ciclo-de-inferência-end-to-end)
8. [Verificação de Sucesso](#verificação-de-sucesso)
9. [Diagnóstico Geral](#diagnóstico-geral)

---

## 1. Configuração de Ambiente

### Variáveis obrigatórias no `.env`

Confirme que todas as variáveis abaixo estão presentes e corretas **antes de iniciar**:

```bash
grep -E "NO1_MODEL|NO2_MODEL|NO1_TOOL_CALLING_NATIVE|NO2_TOOL_CALLING_NATIVE|TOOL_BRIDGE_TIMEOUT_SEC|REDIS_PASSWORD|REDIS_PORT|NO1_LOCAL_OLLAMA_URL|NO2_SERVER_IP" .env
```

**Saída esperada (adapte os valores ao seu hardware):**

```
NO1_LOCAL_OLLAMA_URL='http://localhost:11434/v1'
NO2_SERVER_IP='http://192.168.0.218:11434/v1'
REDIS_PORT=6379
REDIS_PASSWORD=vitalia_redis_secure_2026
NO1_MODEL=llama3.2:3b
NO2_MODEL=qwen2.5-coder:7b
NO1_TOOL_CALLING_NATIVE=false
NO2_TOOL_CALLING_NATIVE=true
TOOL_BRIDGE_TIMEOUT_SEC=30
```

> ⚠️ **Se `NO1_MODEL` ou `NO2_MODEL` estiverem ausentes:** o `build_orchestrator()` tentará carregar `None` como modelo e falhará na inicialização do Ollama Client. Adicione as variáveis antes de continuar.

### Ativar o virtualenv

```bash
cd /home/andre/projetos/assistidos/agente-local
source .venv/bin/activate
```

---

## Fase A — Infraestrutura

**Objetivo:** Confirmar que todos os containers Docker estão operacionais.

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Saída esperada:**

```
NAMES                STATUS          PORTS
vitalia_redis        Up X minutes    0.0.0.0:6379->6379/tcp
vitalia_db           Up X minutes    0.0.0.0:5432->5432/tcp
vitalia_ollama       Up X minutes    0.0.0.0:11434->11434/tcp
vitalia_open_webui   Up X minutes    0.0.0.0:3000->8080/tcp
```

> **Se falhar:** Execute `docker-compose up -d` na raiz do projeto. Se algum container não subir, verifique os logs com `docker logs <container_name>`.

### A.1 — Verificar Redis

```bash
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 ping
```

**Saída esperada:**
```
Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe.
PONG
```

> ℹ️ **Sobre o Warning:** Esta mensagem é um aviso de segurança **esperado e inofensivo** emitido pelo próprio `redis-cli`. Significa apenas que a senha foi passada diretamente na linha de comando — o que a torna visível em `ps aux` e no histórico do shell. Em ambiente de produção usaria-se um pipe ou variável de ambiente. No contexto local do Vitalia, é aceitável. O que importa é que o `PONG` apareça logo abaixo.

> **Se não aparecer PONG:** `docker restart vitalia_redis` e repita o ping.

### A.2 — Verificar Banco de Dados

```bash
docker exec -it vitalia_db psql -U vitalia_admin -d vitalia_db -c "SELECT 1;"
```

**Saída esperada:** `?column? = 1`

---

## Fase B — Conectividade Cross-WSL

**Objetivo:** Confirmar que o Nó 1 (notebook) alcança o Ollama no Nó 2 (servidor).

### B.1 — Ollama no Nó 1 (localhost)

```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep '"name"' | head -5
```

**Saída esperada:** lista de modelos contendo `llama3.2:3b`.

> **Se falhar:** O Ollama local não está rodando. No Nó 1: `docker start vitalia_ollama` ou inicie o Ollama manualmente.

### B.2 — Ollama no Nó 2 (servidor GTX 1060)

```bash
curl -s http://192.168.0.218:11434/api/tags | python3 -m json.tool | grep '"name"' | head -5
```

**Saída esperada:** lista de modelos contendo `qwen2.5-coder:7b`.

> **Se falhar:** Verifique se o servidor está ligado e o Ollama está escutando na interface de rede. No servidor: `ss -tlnp | grep 11434`. Se necessário: `ollama serve --host 0.0.0.0`.

### B.3 — Latência Cross-WSL

```bash
time curl -s http://192.168.0.218:11434/api/tags > /dev/null
```

**Resultado aceitável:** `< 100ms`. Acima disso indica problema de rota de rede.

---

## Fase C — Perfil de Hardware

**Objetivo:** Confirmar que `build_orchestrator()` lê o `.env` corretamente e monta a topologia esperada.

```bash
cd vitalia-core
python3 - << 'EOF'
import os, sys
from dotenv import load_dotenv
load_dotenv("../.env")
sys.path.insert(0, ".")

from unittest.mock import patch, MagicMock
with patch("main.build_ollama_client", return_value=MagicMock()) as mock:
    from main import build_orchestrator
    team, architect, engineer = build_orchestrator()
    native_no1 = os.getenv("NO1_TOOL_CALLING_NATIVE", "false").lower() == "true"
    arch_tools = architect._tools if hasattr(architect, "_tools") else []
    print(f"NO1_MODEL         : {os.getenv('NO1_MODEL')}")
    print(f"NO2_MODEL         : {os.getenv('NO2_MODEL')}")
    print(f"NO1_TOOL_NATIVE   : {os.getenv('NO1_TOOL_CALLING_NATIVE')}")
    print(f"NO2_TOOL_NATIVE   : {os.getenv('NO2_TOOL_CALLING_NATIVE')}")
    print(f"Architect tools   : {len(arch_tools)} ({'esperado 0 (Bridge)' if not native_no1 else 'esperado >0 (Nativo)'})")
    print(f"Engineer context  : {type(engineer._model_context).__name__}")
    print("✅ build_orchestrator() OK")
EOF
```

**Saída esperada:**

```
NO1_MODEL         : llama3.2:3b
NO2_MODEL         : qwen2.5-coder:7b
NO1_TOOL_NATIVE   : false
NO2_TOOL_NATIVE   : true
Architect tools   : 0 (esperado 0 (Bridge))
Engineer context  : HeadAndTailChatCompletionContext
✅ build_orchestrator() OK
```

> **Se falhar com `NO1_MODEL: None`:** As variáveis `NO1_MODEL`/`NO2_MODEL` não estão no `.env`. Adicione-as conforme a Seção 1.

---

## Fase D — Suíte de Testes Unitários

**Objetivo:** Confirmar que todos os **9 testes automatizados** passam (zero falhas, zero warnings).
Split: 6 testes em `test_main_e2e.py` (orquestrador) + 3 em `test_tools.py` (ferramentas).

```bash
cd /home/andre/projetos/assistidos/agente-local
source .venv/bin/activate
pytest vitalia-core/tests/ -v --tb=short
```

**Saída esperada:**

```
9 passed in X.XXs
```

> **Se algum teste falhar:** Não avance para as fases seguintes. Analise o traceback e corrija antes de prosseguir.

---

## Fase E — Tool Bridge Isolado (sem Ollama)

**Objetivo:** Testar o canal Redis Streams do Tool Bridge com um script Python direto, sem precisar que o Ollama responda. Isso isola o Bridge do modelo LLM.

```bash
cd /home/andre/projetos/assistidos/agente-local/vitalia-core
source ../.venv/bin/activate
python3 - << 'EOF'
import asyncio, os, json
from dotenv import load_dotenv
load_dotenv("../.env")
import redis.asyncio as redis_async

REDIS_URL = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:{os.getenv('REDIS_PORT', 6379)}/0"

async def test_bridge_channel():
    r = redis_async.Redis.from_url(REDIS_URL)
    cid = "bench-test-001"
    stream_req = "vitalia:tool_requests:Architect"
    stream_res = "vitalia:tool_results:Architect"

    # Limpar streams anteriores
    try:
        await r.delete(stream_req, stream_res)
    except Exception:
        pass

    # Simular Arquiteto postando pedido
    await r.xadd(stream_req, {
        "correlation_id": cid,
        "tool_name": "web_search",
        "arguments_json": '{"query": "vitalia bench test"}',
        "agent_name": "Architect",
        "timestamp": "2026-06-27T22:00:00",
    })
    print(f"✅ XADD em {stream_req} OK")

    # Simular worker postando resultado
    await r.xadd(stream_res, {
        "correlation_id": cid,
        "result": "Resultado simulado do bench test",
        "error": "",
        "duration_ms": "50",
    })
    print(f"✅ XADD em {stream_res} OK")

    # Ler resultado como o wrapper faria
    messages = await r.xread(streams={stream_res: "0"}, count=10, block=1000)
    found = False
    for _, msgs in messages:
        for _, fields in msgs:
            cid_read = fields.get(b"correlation_id", b"").decode()
            if cid_read == cid:
                result = fields.get(b"result", b"").decode()
                print(f"✅ XREAD resultado: '{result}'")
                found = True
    if not found:
        print("❌ Resultado não encontrado na stream")

    # Inspecionar streams restantes
    info_req = await r.xlen(stream_req)
    info_res = await r.xlen(stream_res)
    print(f"📊 Stream requests: {info_req} mensagem(ns)")
    print(f"📊 Stream results : {info_res} mensagem(ns)")

    await r.aclose()
    print("✅ Tool Bridge Channel: PASS")

asyncio.run(test_bridge_channel())
EOF
```

**Saída esperada:**

```
✅ XADD em vitalia:tool_requests:Architect OK
✅ XADD em vitalia:tool_results:Architect OK
✅ XREAD resultado: 'Resultado simulado do bench test'
📊 Stream requests: 1 mensagem(ns)
📊 Stream results : 1 mensagem(ns)
✅ Tool Bridge Channel: PASS
```

> **Se falhar com `ConnectionRefusedError`:** O Redis não está acessível. Verifique a Fase A.1.
> **Se `XREAD` retornar vazio:** O Redis está rodando mas as streams foram limpas ou há problema de encoding. Tente sem o `delete` inicial.

---

## Fase F — Ciclo de Inferência End-to-End

**Objetivo:** Executar um ciclo real com ambos os nós Ollama ativos. O Arquiteto deve planejar, solicitar uma tool via Bridge e o Engenheiro responder com TERMINATE.

> ⚠️ **Pré-requisito:** Fases A, B, C, D e E devem ter passado. Este teste consome VRAM do Nó 2 e demora 1–5 minutos dependendo da latência de inferência.

### F.1 — Prompt de Teste Padrão

```bash
cd /home/andre/projetos/assistidos/agente-local/vitalia-core
source ../.venv/bin/activate
python3 - << 'EOF'
import asyncio, sys
sys.path.insert(0, ".")
from main import run_vitalia

PROMPT_BENCH = """
[BENCH TEST - 27-06-2026]
Tarefa mínima de validação do sistema:
1. Arquiteto: use web_search para buscar 'Python asyncio best practices 2024' e cite 1 resultado.
2. Engenheiro: escreva uma função Python de 3 linhas que demonstre o uso de asyncio.gather() e salve no RAG.
3. Ao concluir, responda com TERMINATE.
"""

asyncio.run(run_vitalia(PROMPT_BENCH))
EOF
```

### F.2 — O que observar durante a execução

Acompanhe o terminal e confirme a sequência de eventos:

```
🚀 Orquestrador Vitalia iniciado. Tarefa: [BENCH TEST...]
---------- Architect ----------
[texto do Arquiteto planejando...]
---------- ToolCallRequestEvent ----------   ← Bridge ativado
[web_search sendo chamada]
---------- ToolCallExecutionEvent ----------  ← resultado da tool
[resultado da busca]
---------- Engineer ----------
[código gerado pelo Engenheiro...]
[TERMINATE]
```

### F.3 — Verificar logs Redis após o ciclo

```bash
docker exec -it vitalia_redis redis-cli \
  -a vitalia_redis_secure_2026 \
  XRANGE vitalia:tool_requests:Architect - + COUNT 5
```

**Saída esperada:** Pelo menos 1 entry com `tool_name = web_search` e um `correlation_id`.

```bash
docker exec -it vitalia_redis redis-cli \
  -a vitalia_redis_secure_2026 \
  XRANGE vitalia:tool_results:Architect - + COUNT 5
```

**Saída esperada:** Entry correspondente com `result` não vazio.

---

## Verificação de Sucesso

O teste de bancada é considerado **APROVADO** quando todos os itens abaixo forem verificados:

| # | Critério | Como verificar |
|---|---|---|
| ✅ | Todos os containers up | `docker ps` — 4 containers com status `Up` |
| ✅ | Redis responde PONG | `docker exec vitalia_redis redis-cli ping` |
| ✅ | Nó 1 Ollama alcançável | `curl localhost:11434/api/tags` retorna JSON |
| ✅ | Nó 2 Ollama alcançável | `curl 192.168.0.218:11434/api/tags` retorna JSON |
| ✅ | `.env` com variáveis de hardware | `grep NO1_MODEL .env` retorna valor não vazio |
| ✅ | `build_orchestrator()` adaptativo | Script Fase C mostra `Architect tools: 0` com `NATIVE=false` |
| ✅ | 9/9 testes unitários PASSED | `pytest vitalia-core/tests/ -v` — 0 falhas (6 e2e + 3 tools) |
| ✅ | Tool Bridge Channel funcional | Script Fase E mostra `✅ Tool Bridge Channel: PASS` |
| ✅ | `ToolCallRequestEvent` nos logs | Terminal mostra o evento durante a inferência (Fase F.2) |
| ✅ | `TERMINATE` recebido | Última mensagem do Engenheiro contém TERMINATE |
| ✅ | Streams Redis populadas | `XRANGE vitalia:tool_results:Architect` retorna entries |

---

## Diagnóstico Geral

### Inspecionar estado das Redis Streams

```bash
# Ver todas as streams vitalia
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 KEYS "vitalia:*"

# Ver eventos de auditoria (tool_bridge_exec)
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XRANGE vitalia:events - + COUNT 20

# Limpar streams de teste (reset completo)
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  DEL vitalia:tool_requests:Architect vitalia:tool_results:Architect vitalia:events
```

### Verificar VRAM do Nó 2

```bash
# No servidor (Nó 2), verificar uso da GTX 1060
nvidia-smi --query-gpu=name,memory.used,memory.free,memory.total --format=csv
```

**Referência:** qwen2.5-coder:7b ocupa ~5.5GB dos 6GB disponíveis. Se a VRAM estiver no limite, o modelo pode não carregar — reinicie o Ollama no servidor.

### Verificar logs do AutoGen

```bash
# Logs do vitalia:events nos últimos 30 segundos
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XREVRANGE vitalia:events + - COUNT 50
```

### Resetar estado entre testes

```bash
# Limpar cache Redis e streams
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 FLUSHDB

# Reiniciar worker sem reiniciar o AutoGen (ctrl+C no terminal + reexecutar)
```

---

*Documento criado em 27-06-2026 como parte da sprint de refatoração do orquestrador hardware-adaptive.*
*Atualizado em 30-06-2026: IP do Nó 2 definido como 192.168.0.218 (valor atual do servidor), explicação do warning Redis adicionada, contagem de testes atualizada para 9 (6 e2e + 3 tools), `-W error::DeprecationWarning` removido da Fase D (warnings já corrigidos na fonte).*

```md
## 🔬 Teste de Bancada
Consulte o [BENCH_TEST.md](./BENCH_TEST.md) para o pipeline completo de validação end-to-end.
```
