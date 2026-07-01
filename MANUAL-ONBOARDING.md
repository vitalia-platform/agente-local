<!-- MANUAL-ONBOARDING.md | Atualizado em: 01-07-2026 15:03:06(GMT-04:00) -->
# Vitalia Agente Local — Manual de Onboarding

> **Audiência:** Colaborador técnico novo ao projeto. Assume conhecimento geral de Python e terminal Linux. Não assume familiaridade com AutoGen, Redis Streams ou arquitetura multi-agente.
> Leia as seções na ordem — cada uma é pré-requisito da próxima.

---

## Índice

1. [O que é o Vitalia?](#1-o-que-é-o-vitalia)
2. [Arquitetura em Camadas](#2-arquitetura-em-camadas)
3. [Pré-requisitos e Instalação](#3-pré-requisitos-e-instalação)
4. [Referência de Configuração (.env)](#4-referência-de-configuração-env)
5. [Pipeline de Validação E2E](#5-pipeline-de-validação-e2e)
6. [Solução de Problemas Comuns](#6-solução-de-problemas-comuns)

---

## 1. O que é o Vitalia?

O Vitalia é um **orquestrador de agentes de IA** que coordena dois modelos de linguagem (LLMs) rodando em máquinas distintas para executar tarefas de desenvolvimento de software de forma colaborativa.

Pense assim: você dá uma tarefa ("implemente uma função Python para X"). Dois agentes entram em ação:

- **O Arquiteto** — pensa, pesquisa na web, toma decisões de design.
- **O Engenheiro** — escreve o código, salva no banco de dados e reporta o que foi feito.

Eles se comunicam em turnos (Round-Robin), mediados pelo framework **AutoGen** da Microsoft.

> [!NOTE]
> **O que é AutoGen?** É um framework Python que orquestra conversas entre múltiplos agentes de IA. Cada agente tem um modelo de linguagem associado, um conjunto de ferramentas (funções Python que pode chamar) e um papel definido. O AutoGen gerencia os turnos, o histórico de mensagens e a condição de parada.

---

## 2. Arquitetura em Camadas

### 2.1 Duas Máquinas, Um Sistema

```
Nó 1 — Notebook (você)          Nó 2 — Servidor (GTX 1060)
─────────────────────           ─────────────────────────────
• Arquiteto (llama3.2:3b)       • Engenheiro (qwen2.5-coder:7b)
• Redis (vitalia_redis)         • Inferência GPU
• pgvector (vitalia_db)
• Dashboard (telemetry_api)
• Open WebUI
```

> [!NOTE]
> **Por que duas máquinas?** Modelos de linguagem grandes exigem muita memória de vídeo (VRAM). O servidor tem uma GPU dedicada (GTX 1060 com 6GB de VRAM) que roda o modelo de código mais poderoso. O notebook roda o modelo mais leve em CPU. Juntos, fazem mais do que qualquer máquina sozinha conseguiria.

### 2.2 O Problema do Tool Calling

Ferramentas são funções Python que o LLM pode "chamar" (ex: pesquisar na web, salvar código no banco). Mas há um problema: o `llama3.2:3b` rodando em CPU no Nó 1 **não sabe chamar ferramentas no formato correto**. Em vez de emitir um comando estruturado, ele escreve um JSON como texto puro na resposta.

### 2.3 A Solução: Tool Bridge

```
LLM no Nó 1 responde:                  O sistema intercepta:
────────────────────────                ─────────────────────────────
{"name": "web_search",       →   VitaliaOllamaClient detecta o JSON
 "arguments": {"query": "x"}}    └─► posta pedido no Redis Stream
                                       └─► tool_worker() executa a função
                                            └─► posta resultado no Redis Stream
                                                 └─► AutoGen recebe como se fosse
                                                     uma chamada de ferramenta normal
```

> [!NOTE]
> **O que é Redis Streams?** Redis é um banco de dados em memória ultra-rápido. Streams são como filas de mensagens persistentes. Cada mensagem tem um ID único gerado pelo Redis. No Vitalia, usamos duas streams por agente: uma para pedidos de ferramentas (`tool_requests`) e outra para os resultados (`tool_results`). A comunicação é assíncrona: o Arquiteto posta o pedido e aguarda; o `tool_worker()` executa e posta o resultado; o Arquiteto recebe e continua.

### 2.4 Fluxo Completo de um Turno

```
1. AutoGen chama o turno do Arquiteto
2. VitaliaOllamaClient.create() envia mensagens ao Ollama (Nó 1)
3. Ollama retorna JSON cru: {"name": "web_search", "arguments": {...}}
4. VitaliaOllamaClient detecta o padrão e gera um correlation_id (UUID)
5. XADD em vitalia:tool_requests:Architect com o correlation_id
6. tool_worker() (rodando em paralelo) lê o pedido via XREAD
7. tool_worker() chama web_search(**args) localmente
8. tool_worker() faz XADD em vitalia:tool_results:Architect com o resultado
9. VitaliaOllamaClient recebe o resultado (asyncio.Event) e retorna FunctionCall
10. AutoGen processa como ToolCallRequestEvent → ToolCallExecutionEvent
11. Próximo turno: Arquiteto vê o resultado e continua o raciocínio
```

### 2.5 Containers Docker

O sistema usa 4 containers gerenciados pelo Docker Compose:

| Container | Papel | Porta |
|---|---|---|
| `vitalia_redis` | Fila de mensagens + cache | `6379` |
| `vitalia_db` | Banco pgvector (memória de código/RAG) | `5432` |
| `vitalia_ollama` | Motor de inferência local (Nó 1) | `11434` |
| `vitalia_open_webui` | Interface web para chat direto com os modelos | `3000` |

> [!NOTE]
> **O que é pgvector?** É uma extensão do PostgreSQL que permite armazenar e buscar vetores (embeddings) — representações matemáticas do significado de texto. Quando o Engenheiro salva código no RAG, o texto é convertido em um vetor numérico e armazenado. Nas próximas sessões, o sistema busca código similar por semântica, não por palavras-chave.

---

## 3. Pré-requisitos e Instalação

### 3.1 O que você precisa ter instalado

- **Docker + Docker Compose** — para rodar os containers
- **Python 3.12+** — para o orquestrador
- **Ollama** — motor de inferência (rodando no container ou nativamente)
- **Acesso de rede** ao Nó 2 (servidor) na porta `11434`

### 3.2 Clonar e preparar o ambiente

```bash
# 1. Entrar no diretório do projeto
cd /home/andre/projetos/assistidos/agente-local

# 2. Ativar o ambiente virtual Python
source .venv/bin/activate

# 3. Verificar que o .env existe
ls -la .env
# Se não existir: cp .env.example .env  → depois edite com seus valores reais
```

> [!NOTE]
> **O que é um ambiente virtual Python (`.venv`)?** É uma pasta isolada com as dependências do projeto, separadas do Python do sistema operacional. Ativar o `.venv` com `source .venv/bin/activate` faz com que `python3` e `pip` do terminal apontem para as versões do projeto, não as globais. O prompt do terminal muda para mostrar `(.venv)` quando está ativo.

### 3.3 Subir a infraestrutura

```bash
# Na raiz do projeto
docker-compose up -d

# Verificar que tudo subiu
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## 4. Referência de Configuração (.env)

O arquivo `.env` é a **fonte da verdade** de toda a configuração do sistema. Nunca tem nomes de modelos ou IPs hardcoded no código Python — tudo vem daqui.

> [!IMPORTANT]
> O `.env` **nunca deve ser commitado ao Git** (está no `.gitignore`). Ele contém senhas e chaves de API. Use o `.env.example` como template para novos colaboradores.

### 4.1 Infraestrutura de Containers

| Variável | Valor padrão | O que configura |
|---|---|---|
| `POSTGRES_DB` | `vitalia_db` | Nome do banco de dados |
| `POSTGRES_USER` | `vitalia_admin` | Usuário do banco |
| `POSTGRES_PASSWORD` | *(defina um segredo)* | Senha do banco |
| `POSTGRES_PORT` | `5432` | Porta exposta pelo container |
| `REDIS_PORT` | `6379` | Porta do Redis |
| `REDIS_PASSWORD` | *(defina um segredo)* | Senha do Redis |
| `DASHBOARD_SECRET_KEY` | *(defina um segredo)* | Chave para gerar tokens JWT do Dashboard |

### 4.2 Endereços de Rede

| Variável | Exemplo | Descrição |
|---|---|---|
| `NO1_LOCAL_OLLAMA_URL` | `http://localhost:11434/v1` | URL do Ollama na sua máquina (Nó 1) |
| `NO2_SERVER_IP` | `http://192.168.0.218:11434/v1` | URL do Ollama no servidor remoto (Nó 2) |

> [!NOTE]
> **Por que `/v1` no final?** O Ollama expõe duas APIs: a API nativa (`/api/`) e uma API compatível com OpenAI (`/v1/`). O AutoGen usa a compatível com OpenAI. O `/v1` é o prefixo dessa API.

### 4.3 Perfis de Hardware — As variáveis mais importantes

| Variável | Valores | Efeito |
|---|---|---|
| `NO1_MODEL` | ex: `llama3.2:3b` | Modelo que o Arquiteto (Nó 1) usará |
| `NO2_MODEL` | ex: `qwen2.5-coder:7b` | Modelo que o Engenheiro (Nó 2) usará |
| `NO1_TOOL_CALLING_NATIVE` | `true` ou `false` | Se `false`: ativa o Tool Bridge para o Nó 1 |
| `NO2_TOOL_CALLING_NATIVE` | `true` ou `false` | Se `false`: ativa o Tool Bridge para o Nó 2 |
| `TOOL_BRIDGE_TIMEOUT_SEC` | `30` | Quantos segundos o Bridge espera o worker responder |

> [!NOTE]
> **Regra prática para `TOOL_CALLING_NATIVE`:** Se o modelo rodar em CPU ou for um modelo pequeno (< 7B parâmetros) sem suporte documentado a function calling no Ollama, use `false`. Se rodar em GPU com modelo ≥ 7B e o Ollama suportar function calling para aquele modelo, use `true`. Em caso de dúvida, `false` é o valor seguro — o Tool Bridge funciona para qualquer modelo.

### 4.4 APIs de Nuvem (opcionais)

```
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Deixe vazios se não for usar serviços em nuvem. O sistema funciona 100% local.

---

## 5. Pipeline de Validação E2E

Execute as fases em ordem. Cada fase é pré-requisito da próxima. Me avise o resultado de cada bloco antes de prosseguir.

### ✅ Pré-voo

```bash
# Navegue para o projeto e ative o ambiente virtual
cd /home/andre/projetos/assistidos/agente-local
source .venv/bin/activate
```

---

### Fase A — Infraestrutura

**Objetivo:** Confirmar que todos os 4 containers estão rodando e respondendo.

```bash
# A.0 — Verificar containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**O que esperar:**
```
NAMES                STATUS          PORTS
vitalia_redis        Up X minutes    0.0.0.0:6379->6379/tcp
vitalia_db           Up X minutes    0.0.0.0:5432->5432/tcp
vitalia_ollama       Up X minutes    0.0.0.0:11434->11434/tcp
vitalia_open_webui   Up X minutes    0.0.0.0:3000->8080/tcp
```

> [!NOTE]
> Se algum container mostrar `Exited` ou não aparecer na lista, execute `docker-compose up -d` na raiz do projeto para subir todos os containers definidos no `docker-compose.yml`.

```bash
# A.1 — Verificar Redis
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 ping
```

**O que esperar:**
```
Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe.
PONG
```

> [!NOTE]
> **O Warning é normal.** O `redis-cli` emite esse aviso sempre que a senha é passada diretamente no comando (fica visível no histórico do terminal). Em ambiente local de desenvolvimento, isso é aceitável. O que confirma o sucesso é o `PONG` na linha seguinte.

```bash
# A.2 — Verificar banco de dados
docker exec -it vitalia_db psql -U vitalia_admin -d vitalia_db -c "SELECT 1;"
```

**O que esperar:** Uma tabela com `?column? = 1`.

---

### Fase B — Conectividade Cross-WSL

**Objetivo:** Confirmar que as duas máquinas se enxergam e os modelos estão disponíveis.

```bash
# B.1 — Ollama no Nó 1 (sua máquina)
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep '"name"' | head -5
```

**O que esperar:** Uma lista de modelos contendo `llama3.2:3b`.

```bash
# B.2 — Ollama no Nó 2 (servidor remoto)
curl -s http://192.168.0.218:11434/api/tags | python3 -m json.tool | grep '"name"' | head -5
```

**O que esperar:** Uma lista contendo `qwen2.5-coder:7b`.

> [!NOTE]
> **Se B.2 falhar com "Connection refused":** O servidor pode estar desligado, ou o Ollama está rodando mas só escuta em `localhost` no servidor (não na interface de rede). Para verificar no servidor, use `ss -tlnp | grep 11434`. Se só mostrar `127.0.0.1`, o Ollama precisa ser configurado para escutar em `0.0.0.0`.

```bash
# B.3 — Latência de rede (deve ser < 100ms para boa performance)
time curl -s http://192.168.0.218:11434/api/tags > /dev/null
```

---

### Fase C — Perfil de Hardware

**Objetivo:** Confirmar que o código lê corretamente as configurações do `.env` e monta a arquitetura certa.

```bash
# C.1 — Verificar variáveis críticas no .env
grep -E "NO1_MODEL|NO2_MODEL|NO1_TOOL_CALLING_NATIVE|NO2_TOOL_CALLING_NATIVE|TOOL_BRIDGE_TIMEOUT_SEC|NO2_SERVER_IP" .env
```

**O que esperar:**
```
NO2_SERVER_IP='http://192.168.0.218:11434/v1'
NO1_MODEL=llama3.2:3b
NO2_MODEL=qwen2.5-coder:7b
NO1_TOOL_CALLING_NATIVE=false
NO2_TOOL_CALLING_NATIVE=true
TOOL_BRIDGE_TIMEOUT_SEC=30
```

```bash
# C.2 — Testar build_orchestrator()
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
    print(f"Architect tools  : {len(arch_tools)} (esperado 0 com NATIVE=false)")
    print(f"Engineer context : {type(engineer._model_context).__name__}")
    print("✅ build_orchestrator() OK")
EOF
```

> [!NOTE]
> **Por que `Architect tools: 0`?** Com `NO1_TOOL_CALLING_NATIVE=false`, o Arquiteto é criado sem ferramentas registradas no AutoGen. Isso é intencional — as ferramentas são executadas externamente pelo `tool_worker()` via Tool Bridge. Se registrássemos as ferramentas no AutoGen *e* usássemos o Bridge, haveria duplicação. O AutoGen não sabe que o Bridge existe — para ele, o Arquiteto simplesmente retorna um `FunctionCall` estruturado.

---

### Fase D — Testes Unitários

**Objetivo:** Garantir que o código está íntegro antes de testar com hardware real.

```bash
cd /home/andre/projetos/assistidos/agente-local
.venv/bin/python -m pytest vitalia-core/tests/ -v --tb=short
```

**O que esperar:** `9 passed` — sem falhas, sem warnings.

| Arquivo de teste | Quantidade | O que testa |
|---|---|---|
| `test_main_e2e.py` | 6 testes | Orquestrador: hardware-adaptive, tool bridge, worker |
| `test_tools.py` | 3 testes | Ferramentas: web_search, save_code_to_rag, update_sprint_state |

> [!NOTE]
> **Por que rodar os testes antes de ligar o Ollama?** Os testes unitários usam mocks (simulações) — eles *não* fazem chamadas reais ao Ollama nem ao Redis. São rápidos (< 5 segundos) e validam que a lógica do código está correta. Se algum falhar aqui, não adianta avançar para as fases seguintes.

---

### Fase E — Tool Bridge Isolado

**Objetivo:** Testar que o canal Redis Streams funciona corretamente, sem precisar do Ollama.

> [!NOTE]
> **Por que testar o Bridge separado?** Esta fase isola o Redis do resto do sistema. Se a Fase F (inferência real) falhar, você saberá se o problema é no Redis (Fase E falhou) ou no Ollama/modelo (Fase E passou mas F falhou). Isolamento de variáveis é a base do diagnóstico.

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

    # Limpar qualquer dado de teste anterior
    try:
        await r.delete(stream_req, stream_res)
    except Exception:
        pass

    # Simular o Arquiteto postando um pedido de ferramenta
    await r.xadd(stream_req, {"correlation_id": cid, "tool_name": "web_search",
        "arguments_json": '{"query": "vitalia bench test"}', "agent_name": "Architect",
        "timestamp": "2026-06-30T20:00:00"})
    print(f"✅ XADD em {stream_req} OK")

    # Simular o tool_worker() postando o resultado
    await r.xadd(stream_res, {"correlation_id": cid, "result": "Resultado simulado",
        "error": "", "duration_ms": "50"})
    print(f"✅ XADD em {stream_res} OK")

    # Simular o wrapper lendo o resultado
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

**O que esperar:**
```
✅ XADD em vitalia:tool_requests:Architect OK
✅ XADD em vitalia:tool_results:Architect OK
✅ XREAD resultado OK
✅ Tool Bridge Channel: PASS
```

---

### Fase F — Inferência End-to-End

> [!CAUTION]
> **Só execute se as Fases A–E passaram.** Esta fase faz chamadas reais aos modelos de linguagem. O `qwen2.5-coder:7b` carrega na VRAM do Nó 2 (~5.5GB de 6GB). O ciclo completo demora **1 a 5 minutos** dependendo da velocidade de inferência.

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

**O que observar no terminal durante a execução:**

```
🚀 Orquestrador Vitalia iniciado. Tarefa: [BENCH TEST...]
---------- Architect ----------
[Arquiteto planejando e decidindo usar web_search...]
---------- ToolCallRequestEvent ----------   ← Bridge ativado!
[web_search sendo solicitada]
---------- ToolCallExecutionEvent ----------  ← resultado chegou
[resultado da busca]
---------- Engineer ----------
[Engenheiro escrevendo o código...]
TERMINATE
```

> [!NOTE]
> **O que é `ToolCallRequestEvent`?** É o momento em que o AutoGen reconhece que o agente quer chamar uma ferramenta. Com o Tool Bridge, este evento é gerado pelo `VitaliaOllamaClient` ao converter o JSON cru em `FunctionCall`. Se você vir esse evento no log, o Bridge está funcionando corretamente.

```bash
# Após o ciclo: verificar se as streams foram populadas
docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XRANGE vitalia:tool_requests:Architect - + COUNT 5

docker exec -it vitalia_redis redis-cli -a vitalia_redis_secure_2026 \
  XRANGE vitalia:tool_results:Architect - + COUNT 5
```

---

### ✅ Checklist de Aprovação

O teste E2E é considerado **APROVADO** quando todos estes itens estiverem verificados:

| # | Critério | Como verificar |
|---|---|---|
| 1 | 4 containers `Up` | `docker ps` |
| 2 | Redis responde `PONG` | Fase A.1 |
| 3 | Banco de dados responde `1` | Fase A.2 |
| 4 | Nó 1 lista modelos com `llama3.2:3b` | Fase B.1 |
| 5 | Nó 2 lista modelos com `qwen2.5-coder:7b` | Fase B.2 |
| 6 | `.env` com todas as variáveis de hardware | Fase C.1 |
| 7 | `Architect tools: 0` com `NATIVE=false` | Fase C.2 |
| 8 | `9 passed` nos testes unitários | Fase D |
| 9 | `✅ Tool Bridge Channel: PASS` | Fase E |
| 10 | `ToolCallRequestEvent` aparece no log | Fase F |
| 11 | `TERMINATE` ao final do ciclo | Fase F |
| 12 | Streams `tool_requests` e `tool_results` populadas | Fase F.3 |

---

## 6. Solução de Problemas Comuns

### "Connection refused" ao pingar o Ollama do Nó 2

**Causa mais comum:** O servidor está ligado, mas o Ollama só escuta em `localhost`.

**Diagnóstico:**
```bash
# No servidor (Nó 2)
ss -tlnp | grep 11434
# Se mostrar 127.0.0.1:11434, o Ollama está restrito à loopback
```

**Solução:** Configure a variável de ambiente `OLLAMA_HOST=0.0.0.0` antes de iniciar o Ollama no servidor, ou adicione ao `docker-compose.yml` do servidor: `OLLAMA_HOST: "0.0.0.0"`.

---

### "NO1_MODEL: None" ao rodar a Fase C

**Causa:** A variável `NO1_MODEL` (ou `NO2_MODEL`) não está no `.env`.

**Solução:**
```bash
echo "NO1_MODEL=llama3.2:3b" >> .env
echo "NO2_MODEL=qwen2.5-coder:7b" >> .env
```

---

### Tool call aparece como `TextMessage` em vez de `ToolCallRequestEvent`

**Causa:** O LLM não gerou o JSON `{name, arguments}` esperado. Pode ter "esquecido" o formato ou não ter interpretado o system_message corretamente.

**O que fazer:** Isso é comportamento do LLM, não um bug no código. Verifique nos logs do Redis se o `vitalia:tool_requests:Architect` tem entradas. Se não tiver, o LLM não gerou JSON — o sistema tratou a resposta como texto normal.

**Mitigação:** Adicionar um exemplo explícito no `system_message` do Arquiteto de como deve solicitar ferramentas.

---

### Worker timeout — "Tool unavailable: worker timeout after 30s"

**Causa mais provável:** O `tool_worker()` não foi lançado. Isso acontece se `NO1_TOOL_CALLING_NATIVE=true` e `NO2_TOOL_CALLING_NATIVE=true` — nesse caso, `run_vitalia()` não lança o worker.

**Diagnóstico:**
```bash
grep "TOOL_CALLING_NATIVE" .env
# Se ambos forem true, o worker não roda — confirme se deveria ser false em algum nó
```

---

### VRAM cheia no Nó 2

**Sintoma:** O Engenheiro trava na inferência ou o Ollama retorna erro de memória.

**Diagnóstico:**
```bash
# No servidor
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv,noheader
```

**Solução:** Reiniciar o Ollama libera a VRAM:
```bash
docker restart vitalia_ollama
```

---

### Dashboard não carrega após login

**Causa comum:** O JWT de 60 minutos expirou, ou o `DASHBOARD_SECRET_KEY` mudou no `.env` após o login.

**Solução:** Fazer logout no Dashboard e autenticar novamente. Se o problema persistir, reinicie a API:
```bash
# Matar o processo da API e relançar
cd vitalia-core
../.venv/bin/uvicorn telemetry_api:app --host 0.0.0.0 --port 8000 --reload
```

> [!NOTE]
> **Como acessar o Dashboard:** Com a API rodando, abra `http://localhost:8000` no browser. A senha é o valor de `DASHBOARD_SECRET_KEY` no seu `.env`.

---

*Vitalia Agente Local | Manual de Onboarding | 30-06-2026*
*Para referência técnica aprofundada e ADRs arquiteturais, consulte o [MANUAL-REFERENCIA.md](./MANUAL-REFERENCIA.md).*
