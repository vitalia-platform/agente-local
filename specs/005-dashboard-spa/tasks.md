# Tasks: Vitalia Dashboard SPA

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Gerado em**: 30-07-2026

---

## MVP Scope

> Implementar **Phase 1 + Phase 2 + Phase 3 (US1)** entrega produto funcionando.
> Phases adicionais são incrementos opcionais que cobrem as demais User Stories.

---

## Phase 1: Backend API Amendment (Spec 003 Gap Analysis)

*Implementação dos contratos no backend FastAPI aprovados na emenda, pré-requisito para o Frontend.*

- [X] T001 Implementar rota `GET /api/nodes` em `vitalia-core/telemetry_api.py` consumindo o HSET `vitalia:nodes:*`.
- [X] T002 Implementar rota `GET /api/queues` em `vitalia-core/telemetry_api.py`.
- [X] T003 Implementar rota `GET /api/queues/{queue_name}` em `vitalia-core/telemetry_api.py` com paginação básica usando `XRANGE`.

---

## Phase 2: Setup & Design System

*Inicialização do ambiente Vite React. Sem label de US.*

- [X] T004 Inicializar projeto Vite React-TS no diretório `vitalia-dashboard` executando npm create.
- [X] T005 [P] Configurar `outDir` no arquivo `vitalia-dashboard/vite.config.ts` apontando para `../vitalia-core/static`.
- [X] T006 [P] Adicionar fontes "DM Sans" e "Space Grotesk" no arquivo `vitalia-dashboard/index.html`.
- [X] T007 [P] Criar arquivo `vitalia-dashboard/src/assets/colors.css` com as variáveis do Design System "UI UX Pro Max" (Dark Mode).

---

## Phase 3: Security Gate & Context Hook

*Dependências bloqueantes (Auth/Estado global). Sem label de US.*

- [X] T008 [P] Criar componente GlassPanel em `vitalia-dashboard/src/components/GlassPanel.tsx`.
- [X] T009 [P] Criar componente NeonButton em `vitalia-dashboard/src/components/NeonButton.tsx`.
- [X] T010 Criar contexto de autenticação em `vitalia-dashboard/src/context/AuthContext.tsx` que gerencia o JWT no localStorage.
- [X] T011 Criar tela de Login (Security Gate) em `vitalia-dashboard/src/pages/Login.tsx` batendo na rota `/api/login`.
- [X] T012 Configurar roteamento protegido em `vitalia-dashboard/src/App.tsx`.

---

## Phase 4: User Story 1 — Telemetry HUD ao Vivo

**Story Goal**: Visualizar telemetria ao vivo com estética polida para detectar gargalos facilmente.
**Independent Test**: Login realizado, tela exibe gráficos de uso da GPU e os tokens piscam conforme o uso.
**Referência**: FR-003, NR-001, NR-002

- [X] T013 [P] [US1] Criar hook `useWebSocket.ts` em `vitalia-dashboard/src/hooks/useWebSocket.ts` para conectar em `/ws/events`.
- [X] T014 [US1] Criar página Telemetry HUD em `vitalia-dashboard/src/pages/Telemetry.tsx` integrando o hook WebSocket.
- [X] T015 [P] [US1] Criar Sidebar / Navbar para navegação principal em `vitalia-dashboard/src/components/Layout.tsx`.

---

## Phase 5: User Story 2 — Configurações e Navegação Rápida

**Story Goal**: Navegar instantaneamente e gerenciar nós/modelos.
**Independent Test**: Acessar aba de Inventário e ver a lista de nós (via /api/nodes), acessar aba Settings e rodar benchmark.
**Referência**: FR-004, FR-006

- [X] T016 [P] [US2] Criar serviço de API Axios em `vitalia-dashboard/src/api/client.ts` injetando o JWT nos headers.
- [X] T017 [P] [US2] Criar página de Node Inventory em `vitalia-dashboard/src/pages/Inventory.tsx` consumindo `/api/nodes`.
- [X] T018 [P] [US2] Criar página de Settings & Benchmark em `vitalia-dashboard/src/pages/Settings.tsx` consumindo `/api/settings` e `/api/benchmark`.

---

## Phase 6: User Story 3 — Queue Inspector

**Story Goal**: Ler payloads JSON das filas do Redis de forma estruturada.
**Independent Test**: Clicar na aba Queue, listar streams à esquerda, clicar num stream e ver os JSONs à direita.
**Referência**: FR-005

- [X] T019 [US3] Criar página Queue Inspector em `vitalia-dashboard/src/pages/QueueInspector.tsx` consumindo `/api/queues` e `/api/queues/{name}`.
- [X] T020 [P] [US3] Integrar componente de visualização de JSON formatado na tela do Queue Inspector.

---

## Phase 7: Polish & Integration

*Qualidade, build final. Sem label de US.*

- [X] T021 Testar build de produção rodando `npm run build` no `vitalia-dashboard`.
- [X] T022 Validar injeção do index.html gerado acessando `localhost:8000` via FastAPI (`vitalia-core/main.py`).

---

## Dependency Graph

```
Phase 1 (Backend API) 
      ↓
Phase 2 (Setup) 
      ↓
Phase 3 (Auth/Gate) 
      ↓
Phase 4 (US1) → Phase 5 (US2) → Phase 6 (US3)
      ↘_______________________________↙
                      ↓
              Phase 7 (Integration)
```

## Parallel Execution

Tasks marcadas [P] dentro da mesma fase podem ser executadas simultaneamente sem conflito.
