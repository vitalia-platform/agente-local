# Tasks: Observability Enhancement

**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)
**Gerado em**: 31-07-2026

---

## MVP Scope

> Implementar **Phase 1 + Phase 2 + Phase 3 (US1)** entrega produto funcionando (RAG debuggável e Criptografado).
> Phase 4 (US2) é um incremento para robustez do pipeline de Orquestração.

---

## Phase 1: Setup & TDD

*Inicialização do ambiente de testes. Sem label de US.*

- [X] T001 Adicionar pytest e psycopg2-binary no `requirements.txt` ou ambiente local.
- [X] T002 Criar arquivo base em `vitalia-core/tests/test_tools.py`
- [X] T003 Escrever teste TDD (E2E) para `save_code_to_rag` com teardown sanitizado em `vitalia-core/tests/test_tools.py`

---

## Phase 2: Foundational (Logger & Criptografia)

*Dependências bloqueantes. O logger é a Single Source of Truth.*

- [X] T004 [P] Instalar a biblioteca `cryptography`
- [X] T005 [P] Adicionar a pasta `/logs` ao `.gitignore` na raiz do projeto.
- [X] T006 Implementar classe de criptografia simétrica (Fernet) usando `.env` (`HMAC_MASTER_SECRET`) em `vitalia-core/logger.py`
- [X] T007 Implementar gravação unificada com fallback (`data_storage` / `/logs`) e criptografia de payloads em `vitalia-core/logger.py`

---

## Phase 3: User Story 1 — Tool Instrumentation

**Story Goal**: Garantir que ferramentas críticas falhem de forma auditável e documentada.
**Independent Test**: Rodar `pytest vitalia-core/tests/test_tools.py` e verificar console/logs.
**Referência**: FR-002, FR-004, FR-005, FR-007

- [X] T008 [US1] Importar o `logger` global e instrumentar try/except verboso (DB, Redis) em `vitalia-core/tools.py`
- [X] T009 [US1] Atualizar `save_code_to_rag` para ler/escrever da Single Source of Truth criptografada em `vitalia-core/tools.py`

---

## Phase 4: User Story 2 — Orchestrator Polish & Anti-Loop

**Story Goal**: Ajustar `.env` para LLMs fracos e interromper loops infinitos via Orquestrador.
**Independent Test**: Injetar `__VITALIA_ABORT__` via mock e ver se a execução para imediatamente.
**Referência**: FR-001, FR-003, FR-006

- [X] T010 [P] [US2] Mudar `NO2_TOOL_CALLING_NATIVE=true` para `false` em `.env`
- [X] T011 [US2] Injetar a regra `__VITALIA_ABORT__` nos System Prompts dos Agentes em `vitalia-core/main.py`
- [X] T012 [US2] Interceptar `__VITALIA_ABORT__` via `TextMentionTermination` e imprimir a URL exata de roteamento em `vitalia-core/main.py`

---

## Phase N: Polish & Cross-Cutting

*Qualidade e validação da Criptografia*

- [X] T013 Validar se a rota do WebSocket `/ws/events` no `vitalia-core/telemetry_api.py` consegue decriptar os payloads transparentemente, ou se necessita injeção da chave.

---

## Dependency Graph

```text
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → Phase 4 (US2)
                                                         ↘ Phase N
```

## Parallel Execution

Tasks marcadas `[P]` dentro da mesma fase podem ser executadas simultaneamente.
