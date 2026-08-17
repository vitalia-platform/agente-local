# Tasks: Spec 002 — Máquina de Estados e Concorrência Distribuída (Redis Streams + 3-State Lock)

<!-- tasks.md | Atualizado em: 28-07-2026 13:01:00(GMT-04:00) -->

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Gerado em**: 28-07-2026

---

## MVP Scope

> Implementar **Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5** entrega o sistema de concorrência distribuída funcional e seguro, cobrindo todas as User Stories P1.
> Phase 6 (Integração) e Phase 7 (Carga/Observabilidade) são validação e polish — não bloqueantes para o MVP técnico.

---

## Phase 1: Setup — Infraestrutura e Ambiente

*Inicialização do ambiente. Sem label de US. Bloqueante para todas as fases seguintes.*

- [X] T001 Criar estrutura de diretórios: `src/concurrency/`, `src/concurrency/scripts/`, `tests/concurrency/unit/`, `tests/concurrency/integration/`, `tests/concurrency/integration/stress/`
- [X] T002 Criar `src/concurrency/config.py` com `ConcurrencyConfig` via `pydantic-settings` (campos: `REDIS_URL`, `HMAC_MASTER_SECRET`, `HMAC_KEY_TTL_SECONDS=60`, `XREAD_BLOCK_MS=50`, `LOCK_TIMEOUT_MS=5000`)
- [X] T003 Criar `.env.example` com todas as variáveis de `ConcurrencyConfig` documentadas e sem valores sensíveis
- [X] T004 Criar `requirements.txt` com versões fixadas: `redis>=5.0`, `httpx>=0.27`, `pydantic>=2.7`, `pydantic-settings>=2.3`, `uuid6>=2024.01`, `structlog>=24.1`, `pytest>=8.2`, `pytest-asyncio>=0.23`, `fakeredis[aioredis]>=2.23`
- [X] T005 Criar `pyproject.toml` com `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`
- [X] T006 Criar `tests/conftest.py` com fixture `fake_redis` usando `fakeredis.aioredis.FakeRedis()` e fixture `real_redis` condicional via `REDIS_URL` do `.env`
- [X] T007 Validar conexão assíncrona Redis 7.x: script `scripts/check_redis.py` com `await redis.ping()` e print da versão

---

## Phase 2: Foundational — Modelos e Contratos

*Tipos Pydantic e contrato do barramento validados antes de qualquer lógica. Sem label de US.*

- [X] T008 [P] Escrever `tests/concurrency/unit/test_uuid_v7_generation.py` (UT-003): verificar monotonicidade de 1000 UUIDs v7 consecutivos e comparação lexicográfica → **confirmar falha (Red)** *(⚠ [P] relativo a T009 — requer T001 concluído)*
- [X] T009 [P] Implementar `src/concurrency/models.py`: classes `LockState`, `HandshakeStreamEvent`, `AgentAckResponse` (com `DUPLICATE_ACK` no `reaction_code`) e `EphemeralHMACKey` conforme `data-model.md`; usar `uuid6.uuid7()` para `generation_id` *(⚠ [P] relativo a T008 — requer T001 concluído)*
- [X] T010 Confirmar UT-003 passando (Green) após T009
- [X] T011 Implementar `src/concurrency/hmac_manager.py`: funções `generate_ephemeral_key(session_id)`, `sign_payload(payload, key)`, `validate_signature(payload, signature, key)`, `get_key(session_id)` via Redis *(depende de T009 — tipos de `EphemeralHMACKey` e `LockState`)*

---

## Phase 3: User Story 1 — Atomicidade de Trava de 3 Estados via Lua

**Story Goal**: Orquestrador garante que transições de estado são atômicas e o caminho GREEN→RED direto é bloqueado.
**Independent Test**: `pytest tests/concurrency/unit/test_lua_transitions.py -v` (UT-001, UT-005) com `fakeredis`
**Referência**: FR-001, FR-006, FR-007 | SC-001 (zero OOM como consequência de trava correta)

- [X] T012 [P] Escrever `tests/concurrency/unit/test_lua_transitions.py` (UT-001): testar transição sequencial `GREEN→YELLOW→PROPOSING_RED→RED` com 10 tasks concorrentes via `asyncio.gather`; verificar atomicidade → **Red**
- [X] T013 [P] Escrever `tests/concurrency/unit/test_state_machine_rules.py` (UT-005): testar que `GREEN→RED` direto retorna `-1` do script Lua → **Red**
- [X] T014 Implementar `src/concurrency/scripts/transition_state.lua`: validação de estado atual, bloqueio de `GREEN→RED`, comparação lexicográfica de `generation_id`, mutação atômica via Redis Hash
- [X] T015 Implementar `src/concurrency/lock_manager.py`: `LockManager` com métodos `promote_to_yellow(resource_id, agent_id)`, `propose_red(resource_id, agent_id)`, `confirm_red(resource_id)`, `release_red(resource_id)` — cada método executa `transition_state.lua` via `EVALSHA`
- [X] T016 Confirmar UT-001 e UT-005 passando (Green) após T014 e T015

---

## Phase 4: User Story 1 (cont.) + User Story 2 — HMAC Zero-Trust e TTL Dinâmico

**Story Goal**: Todas as mensagens do barramento são autenticadas; chave HMAC não expira durante handshake ativo.
**Independent Test**: `pytest tests/concurrency/unit/test_hmac_ttl_extension.py -v` (UT-004)
**Referência**: FR-004, FR-008 (DUPLICATE_ACK) | SC-002 (100% entrega sob desconexão WSL2)

- [X] T017 [P] Escrever `tests/concurrency/unit/test_hmac_ttl_extension.py` (UT-004): simular lock de 4.9s e verificar que chave HMAC não expirou após `consolidate_acks.lua` chamar `EXPIRE` → **Red**
- [X] T018 [P] Escrever `tests/concurrency/unit/test_ack_deduplication.py` (UT-002): enviar mesmo `event_id` duas vezes; verificar 1ª retorna `CANCELLED_PROMPT`, 2ª retorna `DUPLICATE_ACK` com log WARN e delta de tempo → **Red**
- [X] T019 Implementar `src/concurrency/scripts/consolidate_acks.lua`: verificação de `event_id` já processado (`vitalia:ack:processed:{event_id}`), decremento de contador de ACKs pendentes, promoção para `RED` quando 100%, `EXPIRE` da chave HMAC embutido
- [X] T020 Implementar `src/concurrency/scripts/zombie_cleanup.lua`: marca `ZOMBIE_DISCARDED`, revoga chave HMAC (`DEL`), promove estado para `RED_EXCLUSIVE_WRITE`
- [X] T021 Confirmar UT-004 e UT-002 passando (Green) após T019 e T020

---

## Phase 5: User Story 2 + User Story 3 — Redis Streams, Cancelamento e Resiliência

**Story Goal**: Worker no Nó 2 recebe `CANCEL_INTENT`, cancela inferência em < 150ms e responde com ACK. Agentes zumbi são tratados automaticamente.
**Independent Test**: `pytest tests/concurrency/integration/test_sc003_cancel_timing.py -v` (IT-002) com Redis real
**Referência**: FR-002, FR-003, FR-005 | SC-003 (< 150ms cancelamento local)

- [X] T022 [P] Escrever `tests/concurrency/integration/test_full_handshake.py` (IT-001): handshake completo `PROPOSING_RED → 100% ACKs → RED` com 2 workers; validar < 5000ms → **Red**
- [X] T023 [P] Escrever `tests/concurrency/integration/test_sc003_cancel_timing.py` (IT-002): medir com `time.perf_counter()` o delta entre `XREAD` receber evento e `asyncio.Task.cancel()` ser chamado; assert < 150ms → **Red**
- [X] T024 [P] Escrever `tests/concurrency/integration/test_zombie_discarded.py` (IT-004): iniciar handshake sem worker respondente; aguardar 5000ms; verificar `ZOMBIE_DISCARDED` e estado `RED` liberado → **Red**
- [X] T025 [P] Escrever `tests/concurrency/integration/test_httpx_chunked_cancel.py` (IT-005): inferência de 2000 tokens via `httpx` `stream=True`; disparar cancel após 2 chunks; verificar encerramento em ≤ 3 chunks → **Red**
- [X] T026 Implementar `src/concurrency/stream_publisher.py`: `StreamPublisher.publish_cancel_intent(resource_id, target_agents)` — gera `HandshakeStreamEvent` com UUID v7, assina com HMAC, executa `XADD stream:concurrency:events`
- [X] T027 Implementar `src/concurrency/stream_consumer.py`: loop assíncrono com `XREAD BLOCK 50`, validação HMAC, criação de `asyncio.Task` para inferência com `httpx.AsyncClient(stream=True)`, handler de `asyncio.CancelledError` com `await response.aclose()`, publicação de `AgentAckResponse` em `stream:concurrency:acks`
- [X] T028 Integrar `LockManager` com `StreamPublisher` e `zombie_cleanup.lua`: `propose_red()` dispara publisher; timer assíncrono do `timeout_ms` dispara `zombie_cleanup.lua` se ACKs incompletos
- [X] T029 Escrever `tests/concurrency/integration/test_wsnat_reconnect.py` (IT-003): simular desconexão de 3s via `asyncio.sleep` + `fake_redis.close()`; verificar redelivery correto + `DUPLICATE_ACK` (não segundo `CANCELLED_PROMPT`) → **Red**
- [X] T030 Confirmar IT-001, IT-002, IT-004, IT-005, IT-003 passando (Green)

---

## Phase 6: Testes de Carga e Observabilidade

*Validação de robustez e logging estruturado. Sem label de US.*

- [X] T031 [P] Escrever `tests/concurrency/integration/stress/test_50_red_cycles.py` (LT-001): 50 ciclos `YELLOW → RED → GREEN` consecutivos no mesmo recurso; verificar **SC-001b** (zero vazamento de `asyncio.Task` não cancelada, com mock de inferência LLM — gate de merge; validação SC-001a requer Nó 2 físico) → **Red**
- [X] T032 [P] Escrever `tests/concurrency/integration/stress/test_uuid_v7_stress.py` (LT-002): gerar 100 UUID v7/s por 10 segundos (1000 total); verificar monotonicidade 100% e zero colisão → **Red**
- [X] T033 Implementar `src/concurrency/telemetry.py`: `ConcurrencyLogger` com `structlog`; eventos: `lock_transition`, `cancel_intent_sent`, `ack_received`, `duplicate_ack_detected` (com delta), `zombie_discarded`, `red_promoted`
- [X] T034 Integrar `ConcurrencyLogger` em `lock_manager.py`, `stream_publisher.py` e `stream_consumer.py`
- [X] T035 Confirmar LT-001 e LT-002 passando (Green)

---

## Phase 7: Polish — Documentação e Qualidade Final

*Entregáveis de documentação. Sem label de US. Necessário antes de `/vitalia-spec-implement` considerar a spec "done".*

- [X] T036 Atualizar `README.md` do módulo com: visão geral da máquina de estados, pré-requisitos, comandos de execução e referências ao `quickstart.md`
- [X] T037 Atualizar `.env.example` final com todas as variáveis e comentários explicativos
- [X] T038 Executar suite completa: `pytest tests/concurrency/ -v --tb=short` e garantir 100% passing
- [X] T039 Revisar covertura: `pytest tests/concurrency/ --cov=src/concurrency --cov-report=term-missing`; garantir: Services ≥ 90%, utils ≥ 80% (Artigo III da Constituição)

---

## Dependency Graph

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Models + HMAC base)
    │
    ├──► Phase 3 (US1 — Lua State Machine)
    │         │
    │         ▼
    └──► Phase 4 (US1+US2 — HMAC Zero-Trust + Dedup)
              │
              ▼
         Phase 5 (US2+US3 — Streams + Cancel + Zombie)
              │
              ▼
         Phase 6 (Load + Observability)
              │
              ▼
         Phase 7 (Polish)
```

## Parallel Execution

Tasks marcadas `[P]` dentro da mesma fase podem ser executadas simultaneamente:

| Fase | Tasks paralelizáveis | Nota |
|---|---|---|
| Phase 2 | T008 ↔ T009 (entre si apenas) | Ambas requerem T001; T011 depende de T009 (removido [P]) |
| Phase 3 | T012 + T013 (dois test files independentes) | T014-T016 sequenciais |
| Phase 4 | T017 + T018 (dois test files independentes) | T019-T021 sequenciais |
| Phase 5 | T022 + T023 + T024 + T025 (4 test files independentes) | T026-T030 sequenciais |
| Phase 6 | T031 + T032 (dois stress test files), T033 | T034-T035 sequenciais |

---

## FR Coverage

| FR | Tasks cobrindo | Status |
|---|---|---|
| FR-001 (Máquina 3 estados via Lua) | T012–T016 | ✅ |
| FR-002 (Redis Streams at-least-once) | T022, T026–T030 | ✅ |
| FR-003 (httpx stream=True + XREAD BLOCK 50) | T023, T025, T027 | ✅ |
| FR-004 (HMAC Zero-Trust + EXPIRE Lua) | T017, T019, T011 | ✅ |
| FR-005 (ZOMBIE_DISCARDED timeout) | T020, T024, T028 | ✅ |
| FR-006 (UUID v7 generation_id) | T008–T010, T032 | ✅ |
| FR-007 (Bloqueio GREEN→RED direto) | T013, T014 | ✅ |
| FR-008 (DUPLICATE_ACK + log WARN delta) | T018, T019, T033 | ✅ |

**FRs sem cobertura**: _(nenhum)_ ✅
