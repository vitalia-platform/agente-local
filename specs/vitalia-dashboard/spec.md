<!-- vitalia-dashboard.spec.md | Atualizado em: 24-07-2026 -->
# Especificação: Vitalia Dashboard & Control Plane (Event-Driven)

**Data:** 25-06-2026 (Refatorado em 24-07-2026 para SDD v0.4.0 As-Built)
**Autor/Agente:** Antigravity
**Status:** ⏳ AGUARDANDO APROVAÇÃO

---

## 1. Contexto e Objetivo (O Quê e Por Quê)
O orquestrador gera centenas de eventos em tempo real, tornando a leitura em terminal inviável. Precisamos de um **Control Plane Visual** servido por um backend FastAPI (`telemetry_api.py`) que consume uma stream unificada do Redis (`vitalia_events`) e repassa ao frontend via **WebSocket**. Além disso, o painel deve permitir operações de infraestrutura (restart de containers Docker e testes de benchmark de latência/TPS dos modelos) protegidos por autenticação JWT.

---

## 2. Requisitos Funcionais e Não-Funcionais

### Requisitos Funcionais (FR-xxx)
- **FR-001**: O sistema **MUST** expor um endpoint `/ws/events` que escute a stream Redis `vitalia_events` e repasse dados em tempo real ao client.
- **FR-002**: O sistema **MUST** proteger endpoints críticos de controle (`/api/control/restart`, `/api/settings`, `/api/benchmark`) exigindo token JWT (Bearer).
- **FR-003**: O sistema **MUST** ler o estado da VRAM invocando `nvidia-smi` localmente e devolver um array formatado de GPUs.
- **FR-004**: O sistema **MUST** possuir uma rota `/api/benchmark` que execute warm-up seguido de inferência no Ollama para calcular `Tokens/Sec`.
- **FR-005**: O arquivo `logger.py` **MUST** injetar dados no Redis Stream e realizar Sharding persistindo as cópias no formato `[machine_id].jsonl` no disco.

### Critérios de Sucesso (SC-xxx)
- **SC-001**: O painel **MUST** refletir eventos WebSocket (conversas, uso de tools, logs) sem recarregamento da página (Zero Refresh).
- **SC-002**: A execução do Endpoint de benchmark **MUST** ter fallback de timeout e não travar o loop do FastAPI.

---

## 3. User Stories & Acceptance Scenarios

### User Story 1 - [Monitoramento Unificado via WebSocket] (Priority: P1)
Como Operador do Sistema, quero visualizar todos os eventos (raciocínio, chamadas de ferramentas, conversas) em tempo real, injetados a partir do Event Bus.

**Why this priority**: É impossível debugar de forma efetiva o comportamento assíncrono dos agentes cross-node sem a stream de eventos unificada (P1).

**Independent Test**: Disparar scripts Python simulando `logger.log_event` e checar se o frontend recebe o pacote via socket.

**Acceptance Scenarios**:
1. **Given** que o FastAPI e o Redis estejam online
2. **When** o `logger.py` emitir um evento `type: tool_call` na stream `vitalia_events`
3. **Then** a rota WebSocket (`/ws/events`) irá ler via `XREAD` e repassar para o client, que renderizará visualmente no frontend sem F5.

### User Story 2 - [Benchmark e Configurações de LLM] (Priority: P2)
Como Administrador, quero poder testar as conexões Ollama no painel para validar latência e TPS sem tocar em `.env` ou terminal.

**Why this priority**: Ajuda no troubleshooting sem ser bloqueante para a execução base do orquestrador (P2).

**Independent Test**: Acionar `/api/benchmark` e validar se a API retorna `tokens_per_sec`.

**Acceptance Scenarios**:
1. **Given** a autenticação feita (Token JWT Válido)
2. **When** o endpoint `/api/benchmark` for acionado com a url e o modelo alvo
3. **Then** o sistema fará um post de "Warm-up", outro de "Inference" via HTTPX, calculará o tempo total, e responderá com o `load_duration_ms` e `tokens_per_sec`.

### User Story 3 - [Segurança e Auth no Control Plane] (Priority: P1)
Como Sistema de Infraestrutura, quero que comandos que afetam containers (restart) exijam senha.

**Why this priority**: Impedir acessos não autorizados de destruir as execuções e a infra local.

**Independent Test**: Fazer cURL para `/api/control/restart` sem Bearer Token.

**Acceptance Scenarios**:
1. **Given** a API exposta na porta 8000
2. **When** um usuário tentar acessar `/api/control/restart` sem a `OAuth2PasswordBearer` com um payload JWT válido
3. **Then** a API retornará `401 Unauthorized`.

---

## 4. Glossário
| Termo | Definição |
|---|---|
| **`vitalia_events`** | A stream do Redis onde todos os módulos (Orquestrador, Workers) enviam os dados |
| **Sharding** | Gravação local de backup dos logs no formato `.specify/memory/data_storage/shards/<machine_id>.jsonl` feita por `logger.py` |
| **Control Plane** | Conjunto de APIs de gerência que engloba Docker API (`restart`), Env Control e Benchmark |
