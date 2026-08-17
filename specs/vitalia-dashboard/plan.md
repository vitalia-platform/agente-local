# Implementation Plan: Vitalia Dashboard & Control Plane

**Date**: 24-07-2026 | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/agente-local-v2/specs/vitalia-dashboard/spec.md)

## Summary
Implementação do painel de controle e monitoramento unificado utilizando a leitura em tempo real do barramento de eventos (Redis).

## Technical Context

**Language/Version**: Python 3.11+ / HTML/JS Vanilla
**Primary Dependencies**: FastAPI, WebSockets, `redis-py` (async), `docker`, `PyJWT`
**Storage**: Redis (Hot Cache Stream), Arquivos `.jsonl` para Sharding
**Target Platform**: Navegador Web Moderno
**Project Type**: Web API (Control Plane)
**Performance Goals**: Tempo real (latência WebSocket < 50ms)

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| P01: Isolamento de dados | ✅ PASS | Shards separados por `machine_id` |
| P07: Secrets via .env | ✅ PASS | Tokens e senhas (`DASHBOARD_SECRET_KEY`) são importados exclusivamente do `.env` |

**Resultado**: APROVADO — Arquitetura segura.

## Technical Decisions

1. **FastAPI + WebSockets**: Escolhido pela performance assíncrona. O uso do Uvicorn com WebSockets nativos é ideal para repassar mensagens de Stream sem polling contínuo.
2. **Autenticação via JWT (OAuth2PasswordBearer)**: O FastAPI possui nativamente middlewares para JWT. Isso blinda o control plane de acessos não autorizados locais sem precisar configurar um Keycloak externo.
3. **Leitura Redis Async (`xread`)**: O `telemetry_api.py` utiliza a conexão async do Redis (`redis.asyncio`) ao lado do block de 1000ms para aguardar eventos na stream de forma não-bloqueante para o event-loop da API.

## Project Structure

### Documentation (this feature)
- `specs/vitalia-dashboard/spec.md`
- `specs/vitalia-dashboard/plan.md`
- `specs/vitalia-dashboard/tasks.md`

### Source Code
- `vitalia-core/telemetry_api.py`
- `vitalia-core/logger.py`
- `vitalia-core/static/*`

## Phase Overview

### Phase 1: Setup API & Auth
### Phase 2: Event Logging & Sharding (Unified Bus)
### Phase 3: WebSocket Streaming & Frontend
### Phase 4: Control Plane Operations (Docker, Benchmark)
