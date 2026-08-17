# Contract: Concurrency Lock API — Spec 002

<!-- concurrency_api.md | Atualizado em: 28-07-2026 12:51:00(GMT-04:00) -->

> Interface pública consumida pelos agentes da plataforma Vitalia para coordenação distribuída.
> Toda mensagem no barramento deve ser assinada com HMAC-SHA256 usando a chave efêmera de sessão.

---

## Redis Streams

### Stream: `stream:concurrency:events` (Publisher: Orquestrador Nó 1)

**Propósito**: Notificar workers sobre intenção de escrita exclusiva.

**Mensagem: `CANCEL_INTENT`**

```json
{
  "event_id":      "<UUID v7>",
  "resource_id":   "<string>",
  "action":        "CANCEL_INTENT",
  "target_agents": ["<agent_id_1>", "<agent_id_2>"],
  "timeout_ms":    5000,
  "signature":     "<HMAC-SHA256-hex>"
}
```

**Mensagem: `LOCK_RELEASED`**

```json
{
  "event_id":      "<UUID v7>",
  "resource_id":   "<string>",
  "action":        "LOCK_RELEASED",
  "target_agents": [],
  "timeout_ms":    0,
  "signature":     "<HMAC-SHA256-hex>"
}
```

---

### Stream: `stream:concurrency:acks` (Publisher: Workers Nó 2)

**Propósito**: Confirmar recebimento e execução do cancelamento.

**Mensagem de ACK**

```json
{
  "event_id":     "<UUID v7 — mesmo do evento original>",
  "resource_id":  "<string>",
  "agent_id":     "<string>",
  "reaction_code": "CANCELLED_PROMPT | SAFE_DISCARD | PARTIAL_STATE_FLUSH | ZOMBIE_DISCARDED | DUPLICATE_ACK",
  "timestamp":    "<ISO 8601 UTC>",
  "signature":    "<HMAC-SHA256-hex>"
}
```

---

## Redis Hash: Estado da Trava

**Key**: `vitalia:lock:{resource_id}`

```
HGETALL vitalia:lock:spec-002-concurrency
→ resource_id:              spec-002-concurrency
→ current_state:            YELLOW_SHARED_ANALYTICAL
→ generation_id:            0192f3a4-7c5e-7b3d-8f2a-1e4b5c6d7e8f   (UUID v7)
→ active_analytical_agents: ["agent-analyzer-01","agent-reviewer-02"]
→ proposing_agent_id:       (null)
```

---

## Lua Scripts (Interface Interna)

### `transition_state.lua`

**Assinatura**: `EVAL script 1 {resource_id} {from_state} {to_state} {agent_id} {new_generation_id}`

**Retorno**:
- `1` — transição bem-sucedida
- `0` — transição rejeitada (estado atual ≠ `from_state`)
- `-1` — transição ilegal (ex: GREEN → RED direto)

**Validações obrigatórias dentro do script**:
1. Estado atual == `from_state` (comparação atômica)
2. Caminho GREEN → RED direto → retorna `-1`
3. `generation_id` fornecido é lexicograficamente maior que o atual (prevenção ABA)

---

### `consolidate_acks.lua`

**Assinatura**: `EVAL script 2 {resource_id} {hmac_key_id} {event_id} {agent_id} {reaction_code} {ttl_extend_seconds}`

**Comportamento**:
1. Verifica se `event_id` já está em `vitalia:ack:processed:{event_id}` → retorna `DUPLICATE` se sim
2. Registra `vitalia:ack:processed:{event_id}` com TTL = `LOCK_TIMEOUT_MS/1000 + 1`
3. Decrementa contador de ACKs pendentes para o `event_id`
4. Se todos ACKs recebidos → promove estado para `RED_EXCLUSIVE_WRITE`
5. Executa `EXPIRE vitalia:hmac:session:{hmac_key_id} {ttl_extend_seconds}` (extensão de TTL)

**Retorno**:
- `"OK"` — ACK processado
- `"DUPLICATE"` — `event_id` já processado
- `"RED_PROMOTED"` — todos os ACKs recebidos; trava promovida para RED

---

### `zombie_cleanup.lua`

**Assinatura**: `EVAL script 1 {resource_id} {agent_id} {hmac_key_id}`

**Comportamento**:
1. Registra reação `ZOMBIE_DISCARDED` para `agent_id`
2. Revoga `vitalia:hmac:session:{hmac_key_id}` via `DEL`
3. Promove estado para `RED_EXCLUSIVE_WRITE` (barreira forçada)

---

## Erros e Códigos de Resposta

| Situação | Código / Campo | Descrição |
|---|---|---|
| Transição ilegal (ex: GREEN→RED) | Lua retorna `-1` | Bloqueado pela máquina de estados |
| Estado divergente | Lua retorna `0` | Race condition detectado; retry pelo caller |
| ACK duplicado | `reaction_code: DUPLICATE_ACK` + WARN log | Redelivery do at-least-once; diagnóstico |
| HMAC inválido | Rejeição imediata; evento descartado | Zero-Trust; chave errada ou expirada |
| Timeout handshake | `reaction_code: ZOMBIE_DISCARDED` | Agente não respondeu em `timeout_ms` |

---

## Configuração via `.env`

| Variável | Tipo | Default | Descrição |
|---|---|---|---|
| `REDIS_URL` | `str` | `redis://localhost:6379` | URL do Redis no Nó 1 |
| `HMAC_MASTER_SECRET` | `str` | — (obrigatório) | Secret raiz para derivação de chaves HMAC |
| `HMAC_KEY_TTL_SECONDS` | `int` | `60` | TTL base das chaves efêmeras |
| `XREAD_BLOCK_MS` | `int` | `50` | Máximo 50ms; obrigatório para SC-003 |
| `LOCK_TIMEOUT_MS` | `int` | `5000` | Timeout do handshake antes de ZOMBIE_DISCARDED |
