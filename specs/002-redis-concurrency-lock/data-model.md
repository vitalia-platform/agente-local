# Data Model: Spec 002 — Redis 3-State Concurrency Lock

<!-- data-model.md | Atualizado em: 28-07-2026 12:51:00(GMT-04:00) -->

---

## Entidade: LockState (Estado da Trava de Recurso)

**Armazenamento**: Redis Hash `vitalia:lock:{resource_id}`

| Campo | Tipo | Constraint | Descrição |
|---|---|---|---|
| `resource_id` | `str` | Obrigatório, único | Identificador do arquivo SDD ou código-fonte controlado |
| `current_state` | `Literal["GREEN","YELLOW","PROPOSING_RED","RED"]` | Obrigatório | Estado atual da máquina de estados |
| `generation_id` | `str` (UUID v7) | Obrigatório, monotônico | Versão do recurso; comparação lexicográfica no Lua |
| `active_analytical_agents` | `list[str]` | Default `[]` | IDs dos agentes em leitura analítica ativa |
| `proposing_agent_id` | `str \| None` | Null se não em PROPOSING_RED | ID do agente que solicitou escrita exclusiva |

**Ciclo de vida do estado**:

```
[INIT] ──► GREEN_SHARED_READ
              │
              ▼ (qualquer agente solicita leitura analítica)
           YELLOW_SHARED_ANALYTICAL
              │
              ├─► (todos os agentes analíticos concluem) ──► GREEN_SHARED_READ
              │
              ▼ (Agente A solicita escrita exclusiva)
           PROPOSING_RED
              │
              ├─► (100% ACKs recebidos OU Safety TTL expirado) ──► RED_EXCLUSIVE_WRITE
              │
              └─► (Agente A aborta OU erro Redis) ──► YELLOW_SHARED_ANALYTICAL
                                                           │
                               RED_EXCLUSIVE_WRITE ────────┘
              (SDD atualizado + generation_id++ + lock liberado)
```

**Regra de transição bloqueada**: `GREEN → PROPOSING_RED/RED` **direta é PROIBIDA**.
Todo agente solicitando escrita exclusiva deve passar por `YELLOW` primeiro, garantindo execução do protocolo de handshake.

---

## Entidade: HandshakeStreamEvent (Evento no Redis Stream)

**Armazenamento**: Redis Stream `stream:concurrency:events`

| Campo | Tipo | Constraint | Descrição |
|---|---|---|---|
| `event_id` | `str` (UUID v7) | Obrigatório, único | Identificador para idempotência e deduplicação de ACK |
| `resource_id` | `str` | Obrigatório | Recurso alvo do handshake |
| `action` | `Literal["CANCEL_INTENT","LOCK_RELEASED"]` | Obrigatório | Tipo de evento |
| `target_agents` | `list[str]` | Obrigatório | Agentes que DEVEM responder com ACK |
| `timeout_ms` | `int` | Default `5000` | TTL antes de `ZOMBIE_DISCARDED` (≠ SC-003 local de 150ms) |
| `signature` | `str` (HMAC-SHA256 hex) | Obrigatório | Assinatura com chave efêmera de sessão |

---

## Entidade: AgentAckResponse (ACK no Redis Stream)

**Armazenamento**: Redis Stream `stream:concurrency:acks`

| Campo | Tipo | Constraint | Descrição |
|---|---|---|---|
| `event_id` | `str` (UUID v7) | Obrigatório | UUID v7 do evento original — chave de deduplicação |
| `resource_id` | `str` | Obrigatório | Recurso alvo |
| `agent_id` | `str` | Obrigatório | ID do agente respondendo |
| `reaction_code` | `Literal[...]` | Obrigatório | Ver tabela de códigos abaixo |
| `timestamp` | `datetime` (UTC) | Auto | Momento do ACK |
| `signature` | `str` (HMAC-SHA256 hex) | Obrigatório | Assinatura validando identidade |

**Tabela de `reaction_code`**:

| Código | Significado | Gerado por |
|---|---|---|
| `SAFE_DISCARD` | Worker estava em estado seguro; descartou a tarefa sem perda | Worker em GREEN |
| `CANCELLED_PROMPT` | Inferência ativa cancelada via `asyncio.Task.cancel()` | Worker em YELLOW |
| `PARTIAL_STATE_FLUSH` | Estado parcial descartado; contexto perdido registrado | Worker com estado intermediário |
| `ZOMBIE_DISCARDED` | Orquestrador marcou o agente como zumbi após timeout | Orquestrador (Nó 1) |
| `DUPLICATE_ACK` | ACK duplicado detectado via `event_id` já processado | Orquestrador (rejeição) |

---

## Entidade: EphemeralHMACKey (Chave Efêmera de Sessão)

**Armazenamento**: Redis Key `vitalia:hmac:session:{session_id}` com ACL restrita

| Campo | Descrição |
|---|---|
| **Valor** | 32 bytes aleatórios (HMAC-SHA256 secret) gerados por `secrets.token_bytes(32)` |
| **TTL inicial** | Configurável via `HMAC_KEY_TTL_SECONDS` (default: 60s) |
| **TTL durante lock** | Renovado via `EXPIRE` no Lua `consolidate_acks.lua` a cada ciclo |
| **ACL Redis** | `ACL SETUSER hmac-service ~vitalia:hmac:* +GET +SET +EXPIRE` — sem acesso a outros namespaces |

---

## Mapeamento Redis Keys

| Chave | Tipo | TTL | Propósito |
|---|---|---|---|
| `vitalia:lock:{resource_id}` | Hash | Sem TTL (gerenciado por estado) | Estado da trava |
| `stream:concurrency:events` | Stream | Sem TTL (trimmed manualmente) | Eventos de handshake |
| `stream:concurrency:acks` | Stream | Sem TTL (trimmed manualmente) | Respostas ACK dos workers |
| `vitalia:hmac:session:{id}` | String | `HMAC_KEY_TTL_SECONDS` | Chave efêmera HMAC |
| `vitalia:ack:processed:{event_id}` | String | `LOCK_TIMEOUT_MS / 1000` + 1s | Set de deduplicação de ACKs |
