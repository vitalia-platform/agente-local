<!-- vitalia-orchestrator-refactor.spec.md | Atualizado em: 01-07-2026 15:03:07(GMT-04:00) -->
# Especificação: Orquestrador Hardware-Adaptive com Tool Bridge

**Data:** 27-06-2026
**Autor/Agente:** Antigravity + Andre (sessão de brainstorming 27-06-2026)
**Status:** ⏳ AGUARDANDO APROVAÇÃO

---

## 1. Contexto e Objetivo

### O Problema

O orquestrador Vitalia (`main.py`) tem três falhas estruturais identificadas no brainstorming:

1. **Hardcoding de modelos** — `llama3.2:3b` e `qwen2.5-coder:7b` estão literais no código, ignorando `ROUTER_LLM_PROFILE` e `DEVELOPER_LLM_PROFILE` já definidas no `.env`. Viola o Art. XII da Constituição.

2. **Tool Calling quebrado no Nó 1** — `VitaliaOllamaClient` converte JSONs crus *depois* que o AutoGen já roteou a mensagem como `TextMessage`. O loop entra em estado inconsistente.

3. **Arquitetura sem adaptação de hardware** — qualquer mudança de hardware exige edição de código.

### A Solução

**Perfis de Nó** declarados no `.env` + **Tool Bridge via Redis Streams**: o Arquiteto (Nó com `NATIVE=false`) enfileira pedidos de ferramentas que o `tool_worker()` executa de forma transparente, sem que o AutoGen saiba da mediação.

### Topologia: Atual vs. Target

```
ANTES:
  Arquiteto → VitaliaOllamaClient (parse frágil pós-roteamento) → loop inconsistente

DEPOIS (NATIVE=false):
  Arquiteto → VitaliaOllamaClient → detecta JSON → XADD tool_requests
            ← tool_worker() executa localmente   ← XREAD tool_results
            → retorna FunctionCall ao AutoGen (transparente)

DEPOIS (NATIVE=true):
  Arquiteto → OllamaChatCompletionClient padrão → tool call nativo AutoGen
```

### Hardware Atual de Referência

| Nó | Hardware | `TOOL_CALLING_NATIVE` |
|---|---|---|
| Nó 1 (notebook) | CPU / Swap — llama3.2:3b sem suporte nativo confiável | `false` |
| Nó 2 (servidor GTX 1060 6GB) | GPU — qwen2.5-coder:7b com suporte nativo | `true` |

> **Nota de evolução:** Com GPU de 8GB+ no Nó 1, basta setar `NO1_TOOL_CALLING_NATIVE=true` — zero código alterado.

---

## 2. Requisitos Funcionais

### RF-01 — Perfis de Hardware no `.env`
- [ ] Adicionar ao `.env`: `NO1_MODEL`, `NO2_MODEL`, `NO1_TOOL_CALLING_NATIVE`, `NO2_TOOL_CALLING_NATIVE`, `TOOL_BRIDGE_TIMEOUT_SEC`
- [ ] Documentar todas as novas variáveis no `.env.example` com comentários

### RF-02 — `build_orchestrator()` Hardware-Adaptive
- [ ] Ler `NO1_MODEL` e `NO2_MODEL` do `.env` — sem fallback hardcoded de nome de modelo
- [ ] Se `NO1_TOOL_CALLING_NATIVE=false`: Arquiteto criado **sem** `tools=` no `AssistantAgent`; `VitaliaOllamaClient` (Tool Bridge) é usado
- [ ] Se `NO1_TOOL_CALLING_NATIVE=true`: Arquiteto criado com `tools=`; `OllamaChatCompletionClient` padrão é usado
- [ ] Comportamento simétrico para Nó 2 via `NO2_TOOL_CALLING_NATIVE`

### RF-03 — `VitaliaOllamaClient` — Tool Bridge (modo `NATIVE=false`)
- [ ] Detectar `CreateResult` cujo conteúdo é string JSON com campos `name` e `arguments`
- [ ] Gerar `correlation_id` (UUID4) e postar em `vitalia:tool_requests:<agent_name>`: `{correlation_id, tool_name, arguments_json, agent_name, timestamp}`
- [ ] `XREAD` bloqueante em `vitalia:tool_results:<agent_name>`, filtrando por `correlation_id`, com timeout = `TOOL_BRIDGE_TIMEOUT_SEC`
- [ ] Se resultado: retornar `CreateResult(content=[FunctionCall(...)])`
- [ ] Se timeout: retornar `CreateResult` com string `"Tool unavailable: worker timeout after Xs. Tool: <tool_name>"`
- [ ] Se Redis offline: retornar `CreateResult` com string `"Tool unavailable: Redis connection failed. Tool: <tool_name>"`

### RF-04 — `tool_worker()` — Worker Assíncrono Independente
- [ ] `async def tool_worker()` rodando como `asyncio.Task` paralela ao loop AutoGen
- [ ] Escutar `vitalia:tool_requests:*` com `XREAD BLOCK=500ms` em loop contínuo
- [ ] Ao receber mensagem: localizar função pelo `tool_name` no `TOOL_REGISTRY`, executar com `arguments_json`, capturar resultado ou exceção como string
- [ ] Postar em `vitalia:tool_results:<agent_name>`: `{correlation_id, result, error?, timestamp}`
- [ ] Registrar cada execução em `vitalia:events` via `logger` existente
- [ ] Nunca bloquear o turno do AutoGen — totalmente assíncrono e isolado

### RF-05 — `run_vitalia()` — Lançamento Condicional do Worker
- [ ] Se `NO1_TOOL_CALLING_NATIVE=false` **ou** `NO2_TOOL_CALLING_NATIVE=false`: `asyncio.create_task(tool_worker())` antes do loop
- [ ] Se ambos `true`: nenhum worker lançado

### RF-06 — Resiliência
- [ ] Worker timeout → erro descritivo legível pelo LLM (RF-03) — sem crash
- [ ] Erro auditado em `vitalia:events`: `{event: "tool_bridge_error", tool_name, agent_name, reason}`

### RF-07 — Limpeza de Código Morto
- [ ] Deletar `vitalia-core/tests/test_mock.py`
- [ ] Deletar `vitalia-core/tests/test_mock2.py`
- [ ] Deletar `vitalia-core/tests/test_parse.py`
- [ ] Deletar `Tudo.md` da raiz do projeto

### RF-08 — Reescrita de `test_main_e2e.py` (TDD — Red primeiro)
- [ ] `test_native_false_architect_has_no_tools`: com `NATIVE=false`, Arquiteto não tem tools no `AssistantAgent`
- [ ] `test_native_true_architect_has_tools`: com `NATIVE=true`, Arquiteto tem tools registradas
- [ ] `test_orchestrator_reads_model_from_env`: `build_ollama_client` chamado com modelo do `.env` (não hardcoded)
- [ ] `test_engineer_has_context_limiter`: Engenheiro tem `HeadAndTailChatCompletionContext` (mantido da suíte atual)
- [ ] `test_tool_worker_posts_result_to_stream`: worker consome request e posta result (Redis mockado)
- [ ] `test_vitalia_client_bridges_tool_on_json`: cliente detecta JSON, posta stream, retorna `FunctionCall` (Redis mockado)

---

## 3. Requisitos Não-Funcionais

### RNF-01 — Zero Hardcoding (Art. XII)
Nenhum nome de modelo em `main.py`. Apenas no `.env`.

### RNF-02 — Transparência para o AutoGen (Art. XIV)
Tool Bridge invisível para o framework. `AssistantAgent` não modificado. Toda mediação dentro de `VitaliaOllamaClient.create()`.

### RNF-03 — Sem Nova Dependência (Art. XVII)
Usa exclusivamente Redis (presente), asyncio (stdlib) e `tools.py` existente.

### RNF-04 — Timeout Configurável
`TOOL_BRIDGE_TIMEOUT_SEC` no `.env`, default `30`. Nenhum valor hardcoded em Python.

### RNF-05 — Auditoria (Art. XV)
Toda execução via Tool Bridge registrada em `vitalia:events`:
`{event: "tool_bridge_exec", tool_name, agent_name, correlation_id, duration_ms, error?}`

### RNF-06 — Cobertura Mínima (Art. III)

| Módulo | Mínimo |
|---|---|
| `VitaliaOllamaClient` (bridge logic) | ≥ 90% |
| `tool_worker()` | ≥ 90% |
| `build_orchestrator()` (adaptive logic) | ≥ 80% |

### RNF-07 — Limpeza Idempotente
Deleção dos arquivos mortos não quebra nenhum import ativo nem referência em produção.

### RNF-08 — Timestamp (Art. XV)
`# arquivo.py | Atualizado em: DD-MM-YYYY HH:MM:SS(GMT-04:00)` em todo arquivo criado ou modificado.

---

## 4. Histórias de Usuário

**US-01:** Como **operador**, quero declarar no `.env` se cada nó suporta Tool Calling nativo para que o orquestrador adapte sem edição de código.

**US-02:** Como **Arquiteto rodando em CPU**, quero solicitar `web_search` e receber resultado no mesmo turno, sem GPU.

**US-03:** Como **desenvolvedor**, quero que ao evoluir o hardware baste mudar o `.env` — sem tocar em Python.

**US-04:** Como **operador**, quero ver nos logs quais ferramentas foram via Tool Bridge, com latência e erros.

**US-05:** Como **desenvolvedor**, quero que scripts de debug abandonados e snapshots desatualizados sejam removidos do repositório.

---

## 5. Critérios de Aceite

### CA-01 — Leitura do `.env`
- **Dado** `.env` com `NO1_MODEL=mistral:7b` e `NO1_TOOL_CALLING_NATIVE=true`
- **Quando** `build_orchestrator()` é chamado
- **Então** `build_ollama_client` recebe `model="mistral:7b"` e Arquiteto tem `tools` — **sem editar `main.py`**

### CA-02 — Arquiteto sem tools quando `NATIVE=false`
- **Dado** `NO1_TOOL_CALLING_NATIVE=false`
- **Quando** Arquiteto é construído
- **Então** `AssistantAgent` não recebe `tools=`

### CA-03 — Execução transparente via Bridge
- **Dado** LLM retorna `{"name": "web_search", "arguments": {"query": "x"}}`
- **Quando** `VitaliaOllamaClient.create()` processa
- **Então** `web_search` é executada pelo `tool_worker` e retorna como `CreateResult(content=[FunctionCall(...)])` no **mesmo turno**
- **E** AutoGen processa como `ToolCallRequestEvent` (não `TextMessage`)

### CA-04 — Timeout com erro descritivo
- **Dado** `tool_worker` não responde em `TOOL_BRIDGE_TIMEOUT_SEC` segundos
- **Então** wrapper retorna `"Tool unavailable: worker timeout after Xs. Tool: web_search"`
- **E** sistema não crasha

### CA-05 — Paralelismo Worker / Engenheiro
- **Dado** Engenheiro em inferência e Arquiteto solicitando tool
- **Então** ambos ocorrem em paralelo (verificável por timestamps em `vitalia:events`)

### CA-06 — Testes passam (Red → Green)
- `pytest vitalia-core/tests/` → 0 falhas, 0 erros
- Nenhum teste contém `"llama3.2:3b"` ou `"qwen2.5-coder:7b"` hardcoded

### CA-07 — Limpeza sem regressão
- Após deleção dos 4 arquivos: `pytest` não reporta `ImportError`, cobertura não regressou

### CA-08 — Timeout configurável
- **Dado** `TOOL_BRIDGE_TIMEOUT_SEC=10` no `.env`
- **Então** wrapper usa timeout de 10s (verificável via mock Redis no teste)

---

## 6. Fora do Escopo

- ❌ Migração de framework (AutoGen permanece)
- ❌ Suporte a mais de 2 nós nesta spec
- ❌ Persistência de resultados em pgvector
- ❌ UI para visualizar a fila no dashboard
- ❌ Retry automático de ferramentas que falharam
- ❌ Múltiplas instâncias simultâneas de `run_vitalia()`
- ❌ Atualização de `Progresso.md` — responsabilidade do operador pós-validação

---

## 7. Diagrama de Fluxo (Bússola para o Turno de Código)

```
.env
  NO1_MODEL=llama3.2:3b           NO2_MODEL=qwen2.5-coder:7b
  NO1_TOOL_CALLING_NATIVE=false   NO2_TOOL_CALLING_NATIVE=true
  TOOL_BRIDGE_TIMEOUT_SEC=30
        │
        ▼
build_orchestrator()
  no1_model  = os.getenv("NO1_MODEL")
  no2_model  = os.getenv("NO2_MODEL")
  native_no1 = os.getenv("NO1_TOOL_CALLING_NATIVE","false").lower() == "true"
  native_no2 = os.getenv("NO2_TOOL_CALLING_NATIVE","true").lower()  == "true"

  SE native_no1:
    architect_client = OllamaChatCompletionClient(model=no1_model)
    architect = AssistantAgent(tools=[web_search, query_audit_log, load_dynamic_skill])
  SE NOT native_no1:
    architect_client = VitaliaOllamaClient(model=no1_model)  ← Bridge ativo
    architect = AssistantAgent()                              ← sem tools

  SE native_no2:
    engineer_client = OllamaChatCompletionClient(model=no2_model)
    engineer = AssistantAgent(tools=[save_code_to_rag, update_sprint_state, ...])
  SE NOT native_no2:
    engineer_client = VitaliaOllamaClient(model=no2_model)   ← Bridge ativo
    engineer = AssistantAgent()                               ← sem tools

run_vitalia(task)
  SE NOT native_no1 OR NOT native_no2:
    asyncio.create_task(tool_worker())
  await Console(team.run_stream(task=task))

════════════════════════ FLUXO PARALELO ════════════════════════════

AutoGen Loop                              tool_worker() [asyncio.Task]
────────────────────────────────          ──────────────────────────────
Turno: Arquiteto                          loop:
  VitaliaOllamaClient.create()              XREAD vitalia:tool_requests:*
  LLM retorna JSON cru:                       BLOCK=500ms
  {"name":"web_search","arguments":{...}}
  │
  ├─ detecta JSON de tool call
  ├─ correlation_id = str(uuid4())
  ├─ XADD vitalia:tool_requests:Architect ──► recebe {correlation_id, tool_name, args}
  │    {correlation_id, tool_name, args}        fn = TOOL_REGISTRY[tool_name]
  │                                             result = fn(**json.loads(args))
  ├─ XREAD vitalia:tool_results:Architect  ◄── XADD vitalia:tool_results:Architect
  │    BLOCK = TIMEOUT_SEC * 1000ms              {correlation_id, result}
  │    filtra por correlation_id                logger.log_event("tool_bridge_exec", ...)
  │
  └─ retorna CreateResult(content=[
         FunctionCall(id=correlation_id, name="web_search", arguments=args_str)
     ])

AutoGen interpreta como ToolCallRequestEvent → ToolCallExecutionEvent
(AutoGen acredita execução local — transparência total)

Turno: Engenheiro
  OllamaChatCompletionClient nativo — sem Bridge
```

---

## 8. Mapa de Arquivos Afetados

| Arquivo | Ação | Mudança Principal |
|---|---|---|
| `.env` | MODIFICAR | + `NO1_MODEL`, `NO2_MODEL`, `NO1_TOOL_CALLING_NATIVE`, `NO2_TOOL_CALLING_NATIVE`, `TOOL_BRIDGE_TIMEOUT_SEC` |
| `.env.example` | MODIFICAR | Documentar novas variáveis |
| `vitalia-core/main.py` | MODIFICAR | `build_orchestrator()` adaptativo + `VitaliaOllamaClient` Bridge + `tool_worker()` + `run_vitalia()` condicional |
| `vitalia-core/tests/test_main_e2e.py` | REESCREVER | 6 testes TDD de comportamento (Red → Green) |
| `vitalia-core/tests/test_mock.py` | DELETAR | Código morto |
| `vitalia-core/tests/test_mock2.py` | DELETAR | Código morto |
| `vitalia-core/tests/test_parse.py` | DELETAR | Código morto |
| `Tudo.md` | DELETAR | Snapshot desatualizado |
| `vitalia-core/tools.py` | **SEM MUDANÇA** | Ferramentas intactas |
| `vitalia-core/telemetry_api.py` | **SEM MUDANÇA** | Circuito independente |
| `vitalia-core/static/*` | **SEM MUDANÇA** | Benchmark frontend intacto |
| `docker-compose.yml` | **SEM MUDANÇA** | Redis já suporta Streams |

---

## 9. Glossário

| Termo | Definição |
|---|---|
| **Tool Bridge** | Mecanismo em `VitaliaOllamaClient` que intercepta JSON cru do LLM e media via Redis Streams |
| **`tool_worker()`** | `asyncio.Task` que escuta streams de request, executa ferramentas localmente, posta resultados |
| **`correlation_id`** | UUID4 que une request e response na stream |
| **NATIVE=true** | Nó com Tool Calling nativo — usa `OllamaChatCompletionClient` padrão |
| **NATIVE=false** | Nó sem Tool Calling nativo — usa `VitaliaOllamaClient` com Bridge |
| **`vitalia:tool_requests:<agent>`** | Redis Stream de pedidos de execução |
| **`vitalia:tool_results:<agent>`** | Redis Stream de resultados |
| **`TOOL_REGISTRY`** | Dict interno `{tool_name: callable}` mapeado a partir de `tools.py` |
