# Quickstart: Spec 002 — Redis 3-State Concurrency Lock

<!-- quickstart.md | Atualizado em: 28-07-2026 12:51:00(GMT-04:00) -->

---

## Pré-requisitos

- Redis 7.x rodando no Nó 1 (`redis-server` ou Docker)
- Python 3.11+ com `virtualenv` ativado
- `.env` configurado com `HMAC_MASTER_SECRET` e `REDIS_URL`

```bash
# Instalar dependências
pip install -r requirements.txt

# Copiar e configurar variáveis
cp .env.example .env
# Editar HMAC_MASTER_SECRET com valor seguro de 32+ caracteres
```

---

## Cenário 1: Handshake Completo (US-2 — mapeado a IT-001)

Simula dois agentes em `YELLOW_SHARED_ANALYTICAL`, com o Agente A solicitando escrita exclusiva e o Agente B cancelando sua inferência.

```bash
# Terminal 1 — Iniciar worker consumidor (simula Nó 2)
python -m concurrency.stream_consumer --agent-id agent-b --resource spec-test-001

# Terminal 2 — Disparar handshake como orquestrador (simula Nó 1)
python -m concurrency.lock_manager \
  --resource spec-test-001 \
  --action propose-red \
  --proposing-agent agent-a
```

**Esperado**:
1. `stream_consumer` recebe `CANCEL_INTENT` em < 150ms (SC-003)
2. `stream_consumer` loga `asyncio.Task.cancel()` chamado
3. `stream_consumer` publica `CANCELLED_PROMPT` em `stream:concurrency:acks`
4. `lock_manager` promove para `RED_EXCLUSIVE_WRITE` e loga `RED_PROMOTED`

---

## Cenário 2: Timeout ZOMBIE_DISCARDED (US-3 — mapeado a IT-004)

Simula um agente que não responde ao handshake dentro do `timeout_ms`.

```bash
# Sem iniciar o worker (simula Nó 2 offline)
python -m concurrency.lock_manager \
  --resource spec-test-002 \
  --action propose-red \
  --proposing-agent agent-a \
  --target-agents agent-b-offline
```

**Esperado**:
1. Após 5000ms, `lock_manager` loga `ZOMBIE_DISCARDED` para `agent-b-offline`
2. `lock_manager` promove para `RED_EXCLUSIVE_WRITE`
3. Log de auditoria registra o evento com timestamp

---

## Cenário 3: ACK Duplicado (mapeado a UT-002)

```bash
# Executar suite de testes unitários
pytest tests/concurrency/unit/test_ack_deduplication.py -v
```

**Esperado**:
```
test_first_ack_returns_cancelled_prompt   PASSED
test_duplicate_ack_returns_duplicate_code PASSED
test_duplicate_ack_logs_warn_with_delta   PASSED
```

---

## Cenário 4: Verificação de Tempo SC-003 (mapeado a IT-002)

```bash
pytest tests/concurrency/integration/test_sc003_cancel_timing.py -v -s
```

**Esperado**:
```
[TIMING] XREAD received event → asyncio.Task.cancel() called: 78ms
✓ SC-003 PASS: 78ms < 150ms
```

---

## Executar Suite Completa de Testes

```bash
# Unit tests (fakeredis — sem Redis real)
pytest tests/concurrency/unit/ -v

# Integration tests (requer Redis real em REDIS_URL)
pytest tests/concurrency/integration/ -v --timeout=10

# Stress tests
pytest tests/concurrency/integration/stress/ -v --timeout=120
```
