# Implementation Plan: Vitalia Dashboard SPA

**Branch**: `005-dashboard-spa` | **Date**: 30-07-2026 | **Spec**: [spec.md](spec.md)

## Summary
Substituir a interface estática legada (HTML/JS) servida pelo FastAPI por uma Single Page Application (SPA) reativa. A nova aplicação será construída em React + Vite + TypeScript, utilizando CSS Modules com o Design System "UI UX Pro Max" (Glassmorphism + Tipografia Moderna via CDNs). A saída do build do Vite (`dist`) será configurada para depositar os arquivos estáticos diretamente em `vitalia-core/static/`.

## Technical Context

**Language/Version**: TypeScript / Node 20+
**Primary Dependencies**: React 18, Vite, React Router DOM (para paginação de abas), Lucide-React (ícones).
**Storage**: localStorage (para token JWT de acesso ao dashboard).
**Testing**: Jest + React Testing Library (para componentes principais).
**Target Platform**: Web Browser (Chrome/Edge/Firefox) - Desktop focado.
**Project Type**: Web App (SPA)
**Performance Goals**: Conexão WebSocket imediata sem frame drops (60fps); transição instantânea entre abas (< 100ms).
**Constraints**: Sem uso de TailwindCSS (mandatório). API-First: o desenvolvimento do frontend depende da implementação prévia das rotas listadas em `AMENDMENT_PROPOSAL_SPEC_003.md`.

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| P01: Isolamento de dados | ✅ PASS | O frontend não manipula dados clínicos ou PII, apenas métricas efêmeras do sistema. |
| P06: Segredos Nunca no Git | ✅ PASS | A senha mestra nunca será mockada. JWT fica estritamente na memória e storage do cliente, sem vazar em logs. |
| P12: Desacoplamento Limpo | ✅ PASS | O frontend não terá lógicas de negócios intrínsecas (Zero Hardcoding); tudo baseia-se nas APIs do backend. |
| P13: API-First | ✅ PASS | O planejamento já mapeou as lacunas de contrato (AMENDMENT_PROPOSAL_SPEC_003.md) para alinhar as pontas antes da implementação. |

**Resultado**: APROVADO — prosseguir com planejamento.

## Technical Decisions
Ver as decisões técnicas detalhadas (Frameworks, Estilos, API-First) em [research.md](research.md).

## Project Structure

### Documentation (this feature)
- `specs/005-dashboard-spa/`
  - `spec.md`
  - `plan.md`
  - `research.md`
  - `AMENDMENT_PROPOSAL_SPEC_003.md`
  - `checklists/requirements.md`

### Source Code
- `vitalia-dashboard/` (Novo diretório raiz para o projeto Vite)
  - `package.json`
  - `vite.config.ts` (Configurado com `outDir: '../vitalia-core/static'`)
  - `src/`
    - `api/` (Clientes HTTP Axios/Fetch tipados para o backend)
    - `assets/` (Estilos globais, CSS Variables "Pro Max")
    - `components/` (Componentes reutilizáveis: GlassPanel, NeonButton, etc)
    - `pages/` (Login, Overview, Nodes, Queues, Settings)
    - `App.tsx` & `main.tsx`
- `vitalia-core/static-legacy/` (Backup da versão anterior)
- `vitalia-core/static/` (Pasta autogerida pelo build do Vite)

## Phase Overview

### Phase 1: Setup & Design System
Inicialização do Vite, setup do TypeScript, instalação das fontes (DM Sans / Space Grotesk) via CDN no `index.html`, e definição das variáveis globais CSS Modules (`colors.css`). Configuração do output para `vitalia-core/static/`.

### Phase 2: Security Gate & Context Hook
Criação da tela de Login (Security Gate) integrando com `/api/login`. Criação de um React Context ou Zustand para manter o estado global da sessão e do WebSocket.

### Phase 3: Telemetry HUD & WebSocket Integration
Conversão da interface principal antiga para o padrão Glassmorphism. Integração com o canal de WebSockets (`/ws/events`) para popular os gráficos e os contadores de tokens (Prompt/Completion) e status da GPU (`/api/gpu-status`).

### Phase 4: Node Inventory & Settings
Implementação das abas "Inventário de Nós" (consumindo a nova rota `/api/nodes`) e "Configurações" (consumindo e postando em `/api/settings` e rodando o `/api/benchmark`).

### Phase 5: Queue Inspector (Spec 003 Expansion)
Implementação de visualizador de JSON robusto com suporte a paginação para explorar streams do Redis, consumindo as novas rotas `/api/queues` e `/api/queues/{name}`.

### Phase 6: Build & FastAPI Integration
Verificação ponta-a-ponta rodando `npm run build` e inicializando `telemetry_api.py` para garantir que o FastAPI sirva os chunks `.js` do React sem erro de roteamento (catch-all routes na API se necessário para o React Router).
