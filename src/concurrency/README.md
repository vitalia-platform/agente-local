# Vitalia Concurrency Module

Módulo de concorrência distribuída do Vitalia, garantindo acesso exclusivo a recursos (arquivos, diretórios) e resiliência de estado.

## Visão Geral da Máquina de Estados

A máquina de estados implementa um protocolo de 3 fases (`GREEN` → `YELLOW` → `RED`) protegido por locks atômicos no Redis via scripts Lua, garantindo zero race conditions e tolerância a desconexões de rede (ex: interrupção do WSL).

- `GREEN` (Shared Read): Leitura permitida para todos.
- `YELLOW` (Shared Analytical): Intenção de escrita. Notifica workers para cancelar inferências LLM (limite < 150ms).
- `PROPOSING_RED`: Aguardando 100% de ACKs dos workers alvo.
- `RED` (Exclusive Write): Escrita exclusiva liberada.

## Funcionalidades

- **Lock de 3 Estados**: `transition_state.lua` valida lexicograficamente IDs (UUID v7).
- **HMAC Zero-Trust**: Respostas (ACKs) de workers requerem chave efêmera de sessão, impedindo injects.
- **Deduplicação e Zumbi**: ACKs duplicados são identificados, e timeouts disparam `zombie_cleanup.lua`.

## Pré-requisitos

- Redis 7.x ou superior (suporte a UUID v7 desejável, streams requeridos).
- Python 3.12+
- Variáveis no `.env` (ver `.env.example`).

## Comandos de Execução

- **Testes Unitários**: `.venv/bin/pytest tests/concurrency/unit/ -v`
- **Testes de Integração**: `.venv/bin/pytest tests/concurrency/integration/ -v`
- **Stress Tests**: `.venv/bin/pytest tests/concurrency/integration/stress/ -v`
- **Coverage**: `.venv/bin/pytest tests/concurrency/ --cov=src/concurrency --cov-report=term-missing`

## Referências

- Consulte `specs/002-redis-concurrency-lock/spec.md` para as regras de negócio.
- Consulte `quickstart.md` (quando disponível) para setup rápido do servidor.
