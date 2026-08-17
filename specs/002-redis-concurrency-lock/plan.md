# Implementation Plan: Spec 002 — Máquina de Estados e Concorrência Distribuída (Redis Streams + 3-State Lock)

<!-- plan.md | Atualizado em: 28-07-2026 12:51:00(GMT-04:00) -->

**Branch**: `002-redis-concurrency-lock` | **Date**: 28-07-2026 | **Spec**: [spec.md](./spec.md)

---

## Summary

Implementar a Trava de Concorrência Distribuída de 3 Estados via Redis Lua scripts atômicos, Handshake por Redis Streams com autenticação HMAC-SHA256 e cancelamento assíncrono de inferências no Nó 2 via `asyncio.Task.cancel()`. O sistema garante zero OOM na GTX 1060 e resiliência a oscilações WSL2 NAT.

---

## Technical Context

| Campo | Valor |
|---|---|
| **Language/Version** | Python 3.11+ |
| **Primary Dependencies** | `redis-py >= 5.0` (asyncio nativo), `httpx >= 0.27` (streaming), `pydantic >= 2.7`, `uuid6` (UUID v7), `pytest`, `pytest-asyncio` |
| **Storage** | Redis 7.x (Nó 1: i7-11390H / 32GB RAM) |
| **Testing** | `pytest` + `pytest-asyncio` + `fakeredis[aioredis]` para unit; Redis real para IT |
| **Target Platform** | Server — distribuído (Nó 1 orquestrador + Nó 2 inferência GTX 1060) |
| **Project Type** | Library/Service core — consumida pelos agentes da plataforma Vitalia |
| **Performance Goals** | SC-003: cancelamento local do worker < 150ms (`XREAD BLOCK 50` obrigatório) |
| **Constraints** | GTX 1060 6GB VRAM limite rígido; WSL2 NAT instável; Python AsyncIO single-thread por nó |

---

## Constitution Check

| Princípio | Status | Observação |
|---|---|---|
| Art. I — SDD Pipeline | ✅ PASS | Spec aprovada, plan gerado via `/vitalia-spec-plan` |
| Art. II — Decomposição Atômica | ✅ PASS | 12 testes individuais identificados na spec; fases sequenciais |
| Art. III — Test-First | ✅ PASS | Matriz de testes definida: UT/IT/LT; testes escritos antes da implementação |
| Art. IV — Análise de Impacto | ✅ PASS | Sem dados de saúde; dado sensível = chave HMAC efêmera (coberta por Art. VI) |
| Art. V — Soberania do Dado | ✅ PASS | Sem PII ou dado clínico; `LockState` contém apenas IDs de agentes e estado |
| Art. VI — Segredos fora do Git | ✅ PASS | Chaves HMAC efêmeras em Redis com TTL; `HMAC_MASTER_SECRET` via `.env` |
| Art. VII — Segurança de API | ✅ PASS | Zero-Trust HMAC-SHA256 em todos os eventos do barramento |
| Art. VIII/IX — HITL Saúde | ✅ N/A | Preset: software (sem domínio clínico direto) |
| Art. XII — Zero Hardcoding | ✅ PASS | `timeout_ms`, `XREAD BLOCK` e TTLs via configuração; nenhum valor fixo em código |
| Art. XIII — Contrato-Primeiro | ✅ PASS | `contracts/concurrency_api.md` gerado |
| Art. XIV — YAGNI | ✅ PASS | Sem abstrações extras; Lua direto no Redis sem ORM de lock |
| Art. XV — Timestamp e Auditoria | ✅ PASS | `AgentAckResponse.timestamp` obrigatório; log de DUPLICATE_ACK com delta |
| Art. XVII — Ambiente Reprodutível | ✅ PASS | `requirements.txt` versionado; `fakeredis` isola testes unit |
| Art. XVIII — Observabilidade | ✅ PASS | Structured logging obrigatório; XREAD BLOCK 50 garante < 150ms |

**Resultado**: ✅ APROVADO — prosseguir com planejamento

---

## Technical Decisions

> Detalhes completos em [research.md](./research.md)

| Decisão | Escolha | Resumo da Justificativa |
|---|---|---|
| `generation_id` | UUID v7 (string) | Monotônico, sem overflow, comparação lexicográfica no Lua |
| Entrega confiável | Redis Streams (`at-least-once`) | Resiste a oscilações WSL2 NAT; persistência nativa |
| Atomicidade da trava | Script Lua no Redis | Operação atômica no servidor, zero race conditions |
| Cancelamento de inferência | `asyncio.Task.cancel()` + httpx `stream=True` | Cancelamento imediato sem aguardar payload completo |
| Deduplicação de ACK | Rejeição com `DUPLICATE_ACK` + log WARN | Detecta bugs de redelivery; auditável |
| Extensão de TTL HMAC | `EXPIRE` dentro do Lua de consolidação de ACKs | Previne expiração de chave durante handshake ativo |
| Framework de testes | `pytest-asyncio` + `fakeredis` | Isolamento de unit tests sem Redis real; IT com Redis real |

---

## Project Structure

### Documentation (specs/002-redis-concurrency-lock/)

```
specs/002-redis-concurrency-lock/
├── spec.md              ✅ (aprovada v1.1)
├── plan.md              ✅ (este arquivo)
├── research.md          ✅ (decisões técnicas detalhadas)
├── data-model.md        ✅ (entidades e ciclo de vida)
├── quickstart.md        ✅ (validação executável)
├── tasks.md             ⏳ (gerado por /vitalia-spec-tasks)
└── contracts/
    └── concurrency_api.md  ✅ (contrato do barramento de eventos)
```

### Source Code (estrutura proposta)

```
src/
└── concurrency/
    ├── __init__.py
    ├── config.py              # ConcurrencyConfig (timeout_ms, xread_block_ms, hmac_ttl_s)
    ├── models.py              # LockState, HandshakeStreamEvent, AgentAckResponse (Pydantic)
    ├── lock_manager.py        # Orquestrador: transições de estado via Lua
    ├── scripts/
    │   ├── transition_state.lua   # GREEN→YELLOW→PROPOSING_RED→RED (atômico)
    │   ├── consolidate_acks.lua   # Consolida ACKs + EXPIRE da chave HMAC
    │   └── zombie_cleanup.lua     # Marca ZOMBIE_DISCARDED + libera RED
    ├── stream_publisher.py    # Publica CANCEL_INTENT no Redis Stream
    ├── stream_consumer.py     # Worker: XREAD BLOCK 50 + asyncio.Task.cancel()
    ├── hmac_manager.py        # Geração, distribuição e validação de chaves efêmeras
    └── telemetry.py           # Structured logging de eventos de lock

tests/
└── concurrency/
    ├── unit/
    │   ├── test_lua_transitions.py      # UT-001, UT-005
    │   ├── test_ack_deduplication.py    # UT-002
    │   ├── test_uuid_v7_generation.py   # UT-003
    │   ├── test_hmac_ttl_extension.py   # UT-004
    │   └── test_state_machine_rules.py  # UT-005
    └── integration/
        ├── test_full_handshake.py        # IT-001
        ├── test_sc003_cancel_timing.py   # IT-002
        ├── test_wsnat_reconnect.py       # IT-003
        ├── test_zombie_discarded.py      # IT-004
        ├── test_httpx_chunked_cancel.py  # IT-005
        └── stress/
            ├── test_50_red_cycles.py     # LT-001
            └── test_uuid_v7_stress.py    # LT-002
```

---

## Phase Overview

### Phase 1: Setup e Infraestrutura (Fundação)

**Objetivo**: Ambiente de desenvolvimento reprodutível e configuração base.

- [ ] Criar `src/concurrency/config.py` com `ConcurrencyConfig` via `pydantic-settings`
- [ ] Configurar `pytest.ini` + `conftest.py` com `fakeredis` para unit tests
- [ ] Criar `.env.example` com `HMAC_MASTER_SECRET`, `REDIS_URL`, `XREAD_BLOCK_MS=50`, `LOCK_TIMEOUT_MS=5000`
- [ ] Criar `requirements.txt` versionado e `pyproject.toml`
- [ ] Validar conexão Redis 7.x assíncrona (`redis-py` asyncio)

### Phase 2: Modelos e Contratos (Data Layer)

**Objetivo**: Tipos Pydantic + contrato do barramento validados antes de qualquer lógica.

- [ ] Implementar `src/concurrency/models.py`: `LockState`, `HandshakeStreamEvent`, `AgentAckResponse` (com `DUPLICATE_ACK`)
- [ ] Escrever UT-003 (UUID v7 monotônico) → confirmar falha → implementar `uuid6` → confirmar green
- [ ] Gerar `contracts/concurrency_api.md`
- [ ] Gerar `data-model.md`

### Phase 3: Máquina de Estados Lua (Core Atômico)

**Objetivo**: Transições de estado corretas e bloqueio de caminho ilegal (GREEN→RED direto).

- [ ] Escrever UT-001 (transição GREEN→YELLOW→PROPOSING_RED→RED) → falha
- [ ] Escrever UT-005 (bloqueio GREEN→RED direto) → falha
- [ ] Implementar `scripts/transition_state.lua`
- [ ] Implementar `lock_manager.py` com métodos: `promote_to_yellow()`, `propose_red()`, `confirm_red()`, `release_red()`
- [ ] Confirmar UT-001 e UT-005 green

### Phase 4: HMAC Manager (Zero-Trust)

**Objetivo**: Geração, distribuição e renovação de chaves efêmeras com TTL estendível.

- [ ] Escrever UT-004 (TTL HMAC renovado durante lock ativo) → falha
- [ ] Implementar `hmac_manager.py`: `generate_ephemeral_key()`, `validate_signature()`, `extend_ttl()`
- [ ] Implementar `scripts/consolidate_acks.lua` com `EXPIRE` embutido
- [ ] Confirmar UT-004 green

### Phase 5: Redis Streams — Publisher e Consumer (US-2 e US-3)

**Objetivo**: Handshake completo via streams; cancelamento local < 150ms.

- [ ] Escrever UT-002 (deduplicação de ACK duplicado) → falha
- [ ] Implementar `stream_publisher.py`: `publish_cancel_intent()` com HMAC
- [ ] Implementar `stream_consumer.py`: `XREAD BLOCK 50`, validação HMAC, `asyncio.Task.cancel()`, httpx `stream=True`
- [ ] Implementar `scripts/zombie_cleanup.lua`
- [ ] Confirmar UT-002 green

### Phase 6: Testes de Integração

**Objetivo**: Validar o sistema completo contra Redis real com restrições de hardware.

- [ ] IT-001: Handshake completo PROPOSING_RED → RED < 5000ms
- [ ] IT-002: Medir tempo XREAD→cancel < 150ms com `time.perf_counter()`
- [ ] IT-003: Simular desconexão WSL2 3s → redelivery → DUPLICATE_ACK correto
- [ ] IT-004: Timeout 5000ms → ZOMBIE_DISCARDED → RED liberado
- [ ] IT-005: Inferência de 2000 tokens via httpx stream → cancel interrompe em ≤ 3 chunks

### Phase 7: Testes de Carga e Observabilidade

**Objetivo**: Validar robustez sob carga e garantir logging estruturado.

- [ ] LT-001: 50 ciclos RED consecutivos → SC-001 (zero OOM)
- [ ] LT-002: 100 UUID v7/s → monotonicidade validada
- [ ] Implementar `telemetry.py` com structured logging (`structlog`)
- [ ] Atualizar `README.md` e `.env.example`

---

## Relatório de Conclusão do Plan

```
Plan gerado:   specs/002-redis-concurrency-lock/plan.md    ✅
Constitution Check:                                         ✅ APROVADO (13/13)
Artefatos auxiliares:
  research.md    ✅
  data-model.md  ✅
  contracts/     ✅
  quickstart.md  ✅

Próximo passo: /vitalia-spec-tasks
```
