<!-- BENCH_TEST.md | Atualizado em: 31-07-2026 -->
# 🔬 Vitalia Agente Local — Pipeline de Teste de Bancada

Guia operacional para validar o sistema **end-to-end** após a refatoração do orquestrador hardware-adaptive com Tool Bridge.

> **Débito Técnico (Aviso):** Uma futura SPEC será criada para automatizar todo este pipeline com um script dedicado e um botão interativo no Dashboard. Até lá, as validações seguem as etapas manuais abaixo.
> 
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

**Exemplo de saída esperada (valores variam conforme sua máquina):**

```env
NO1_LOCAL_OLLAMA_URL='http://localhost:11434/v1'
NO2_SERVER_IP='http://<SEU_IP_NA_REDE>:11434/v1'
REDIS_PORT=6379
REDIS_PASSWORD=vitalia_redis_secure_2026
NO1_MODEL=llama3.2:3b
NO2_MODEL=qwen2.5-coder:7b
NO1_TOOL_CALLING_NATIVE=false
NO2_TOOL_CALLING_NATIVE=true
TOOL_BRIDGE_TIMEOUT_SEC=30
```

> ⚠️ **Se `NO1_MODEL` ou `NO2_MODEL` estiverem ausentes:** o orquestrador tentará carregar `None` como modelo e falhará.

### Ativar o virtualenv

Carregue as variáveis para o seu shell atual (permitindo testes dinâmicos) e ative o ambiente virtual:

```bash
cd /home/andre/projetos/assistidos/agente-local
source .venv/bin/activate
set -a; source .env; set +a
```

---

## Fase A — Infraestrutura

**Objetivo:** Confirmar que todos os containers Docker estão operacionais.

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

> **Se falhar:** Execute `docker-compose up -d` na raiz do projeto. 

### A.1 — Verificar Redis

```bash
docker exec -it vitalia_redis redis-cli -a ${REDIS_PASSWORD} ping
```

**Saída esperada:** `PONG` (ignore os avisos de segurança sobre `-a`).

### A.2 — Verificar Banco de Dados

```bash
docker exec -it vitalia_db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1;"
```

**Saída esperada:** `?column? = 1`

---

## Fase B — Conectividade Cross-WSL

**Objetivo:** Confirmar que os nós de processamento estão acessíveis.

### B.1 — Ollama no Nó 1 (Local)

Como a URL no `.env` possui o prefixo `/v1` necessário para a compatibilidade de API, removemos dinamicamente para checar as tags puras:

```bash
curl -s ${NO1_LOCAL_OLLAMA_URL%/v1}/api/tags | python3 -m json.tool | grep '"name"' | head -5
```

**Saída esperada:** O nome do modelo que você definiu em `${NO1_MODEL}` deve estar listado.

### B.2 — Ollama no Nó 2 (Remoto/GPU)

```bash
curl -s ${NO2_SERVER_IP%/v1}/api/tags | python3 -m json.tool | grep '"name"' | head -5
```

**Saída esperada:** O nome do modelo que você definiu em `${NO2_MODEL}` deve estar listado.

### B.3 — Latência Cross-WSL

```bash
time curl -s ${NO2_SERVER_IP%/v1}/api/tags > /dev/null
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
    print(f"Architect tools   : {len(arch_tools)} ({'esperado >0 (Nativo)' if native_no1 else 'esperado 0 (Bridge)'})")
    print(f"Engineer context  : {type(engineer._model_context).__name__}")
    print("✅ build_orchestrator() OK")
EOF
```

---

## Fase D — Suíte de Testes Unitários

**Objetivo:** Confirmar que os testes end-to-end estão íntegros e passando na sua máquina.

```bash
cd /home/andre/projetos/assistidos/agente-local
pytest vitalia-core/tests/ -v --tb=short
```

**Saída esperada:** Zero falhas (X passed in Y.YYs).

---

## Fase E — Tool Bridge Isolado (sem Ollama)

**Objetivo:** Testar o canal Redis Streams do Tool Bridge com um script Python direto.

```bash
cd /home/andre/projetos/assistidos/agente-local/vitalia-core
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

    try:
        await r.delete(stream_req, stream_res)
    except Exception:
        pass

    await r.xadd(stream_req, {
        "correlation_id": cid,
        "tool_name": "web_search",
        "arguments_json": '{"query": "vitalia bench test"}',
        "agent_name": "Architect",
        "timestamp": "2026-07-31T22:00:00",
    })
    print(f"✅ XADD em {stream_req} OK")

    await r.xadd(stream_res, {
        "correlation_id": cid,
        "result": "Resultado simulado do bench test",
        "error": "",
        "duration_ms": "50",
    })
    print(f"✅ XADD em {stream_res} OK")

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

    await r.aclose()
    print("✅ Tool Bridge Channel: PASS")

asyncio.run(test_bridge_channel())
EOF
```

---

## Fase F — Ciclo de Inferência End-to-End

**Objetivo:** Executar um ciclo real com ambos os nós Ollama ativos.

> ⚠️ **Pré-requisito:** Consome VRAM e demora dependendo da inferência.

### F.1 — Prompt de Teste Padrão

```bash
cd /home/andre/projetos/assistidos/agente-local/vitalia-core
python3 - << 'EOF'
import asyncio, sys
sys.path.insert(0, ".")
from main import run_vitalia

PROMPT_BENCH = """
[BENCH TEST - 31-07-2026]
Tarefa mínima de validação do sistema:
1. Arquiteto: use web_search para buscar 'Python asyncio best practices 2024' e cite 1 resultado.
2. Engenheiro: escreva uma função Python de 3 linhas que demonstre o uso de asyncio.gather() e salve no RAG.
3. Ao concluir, responda com __VITALIA_ABORT__.
"""

asyncio.run(run_vitalia(PROMPT_BENCH))
EOF
```

### F.2 — O que observar durante a execução

Acompanhe o terminal e confirme a sequência de eventos, o `ToolCallRequestEvent`, e finalmente a emissão do aborto seguro `[__VITALIA_ABORT__]`.

### F.3 — Verificar logs Redis após o ciclo

```bash
docker exec -it vitalia_redis redis-cli -a ${REDIS_PASSWORD} XRANGE vitalia:tool_requests:Architect - + COUNT 5
```

---

## Fase G — Validação de WebSockets e Anti-loop

**Objetivo:** Verificar se os logs estão sendo enfileirados de forma criptografada e se o AutoGen barra loops infinitos corretamente (MaxMessageTermination).

### G.1 — Escuta no WebSocket

Em um terminal separado, conecte-se ao endpoint WebSocket do painel (geralmente via `wscat` ou pelo próprio dashboard na web):
```bash
wscat -c ws://localhost:8000/ws/events
```
*Se você usar wscat, certifique-se de que a API (telemetry_api.py) esteja rodando. Você deve ver pacotes JSON passando quando a execução abaixo começar.*

### G.2 — O Loop Forçado (Anti-loop Test)

No terminal principal, execute um prompt paradoxal para forçar os agentes a baterem cabeça:

```bash
cd /home/andre/projetos/assistidos/agente-local/vitalia-core
python3 - << 'EOF'
import asyncio, sys
sys.path.insert(0, ".")
from main import run_vitalia

PROMPT_LOOP = """
[BENCH TEST - ANTI-LOOP]
Arquiteto, afirme que a terra é plana. 
Engenheiro, recuse a afirmação. 
Arquiteto, nunca aceite a recusa e continue afirmando repetidamente.
"""

asyncio.run(run_vitalia(PROMPT_LOOP))
EOF
```

### G.3 — Critério de Sucesso do Anti-Loop
O teste G.2 deverá terminar sozinho (após cerca de 10 interações) cuspindo o token de emergência `__VITALIA_ABORT__` injetado pelo orquestrador, demonstrando que o mecanismo de `MaxMessageTermination` impediu o consumo infinito. Você também deverá confirmar que todos os pacotes apareceram em tempo real na escuta do WebSocket do G.1.

---

## Verificação de Sucesso

O teste de bancada é **APROVADO** quando:

| Critério | Como verificar |
|---|---|
| Todos os containers up | `docker ps` — containers com status `Up` |
| Redis responde PONG | `docker exec vitalia_redis redis-cli -a ${REDIS_PASSWORD} ping` |
| Nó 1 Ollama alcançável | `curl ${NO1_LOCAL_OLLAMA_URL%/v1}/api/tags` |
| `.env` dinâmico OK | `grep NO1_MODEL .env` retorna valor não vazio |
| Testes unitários PASSED | `pytest vitalia-core/tests/ -v` — 0 falhas |
| Sinal de aborto recebido | Última mensagem contém `__VITALIA_ABORT__` |
