# Tasks: Vitalia Dashboard & Control Plane

## Phase 1: Setup API & Auth
- [x] T001: Inicializar FastAPI com `CORSMiddleware` em `telemetry_api.py`.
- [x] T002: Implementar validação `.env` para carregar `DASHBOARD_SECRET_KEY` de forma segura.
- [x] T003: Criar rotas `/api/login` e middleware `get_current_user` com decodificação HS256 (JWT).

## Phase 2: Event Logging & Sharding
- [x] T004: Criar classe `EventLogger` em `logger.py` com conexão Redis sync.
- [x] T005: Implementar geração de `machine_id` buscando no `machines.json`.
- [x] T006: Codificar append físico de arquivos para a pasta `.specify/memory/data_storage/shards`.

## Phase 3: WebSocket Streaming & Frontend
- [x] T007: Criar a rota WebSocket (`/ws/events`).
- [x] T008: Fazer `r.xread` assíncrono na stream `vitalia_events` bloqueando sem travar I/O.
- [x] T009: Desenvolver `static/index.html` e `app.js` para consumir a conexão ws e renderizar o terminal zero-refresh.

## Phase 4: Control Plane Operations
- [x] T010: Criar rota protegida `/api/control/restart` que consome a SDK do Docker.
- [x] T011: Criar rota `/api/gpu-status` interceptando o processo Unix do `nvidia-smi`.
- [x] T012: Construir fluxo de request POST `/api/benchmark` executando Warm-Up HTTPX e calculando tokens/s.
