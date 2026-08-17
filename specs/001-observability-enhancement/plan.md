# Implementation Plan: Observability Enhancement

**Branch**: `001-observability` | **Date**: 31-07-2026 | **Spec**: [spec.md](../spec.md)

## Summary
Adicionar observabilidade profunda no backend (Orquestrador e Ferramentas) garantindo que o `logger.py` seja a Fonte Única da Verdade (Single Source of Truth) para o fluxo de execuções. Isso inclui logs granulares, fallback de arquivos, mecanismo de terminação anti-loop explícito (`__VITALIA_ABORT__`) e criptografia absoluta dos payloads (Artigo V), além de testes TDD com banco real (E2E).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `redis`, `autogen_agentchat`, `psycopg2`, `cryptography`
**Storage**: Redis Stream (`vitalia_events`), PostgreSQL (`vitalia_db`), Arquivos de Log (fallback)
**Testing**: `pytest`
**Target Platform**: Backend Server / CLI (Cross-WSL)
**Project Type**: Core Orchestrator
**Performance Goals**: Logs em tempo real, sem bloquear o event loop do AutoGen.
**Constraints**: Não modificar a porta ou variáveis do Docker sem necessidade.

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| P01: Isolamento de dados | ✅ PASS | Logs de sistema não extrairão PII. Cargas úteis serão criptografadas via FR-007. |
| P02: Segredos Nunca no Git | ✅ PASS | Nenhuma credencial manipulada, apenas .env lido. |
| P03: Test-First (TDD) | ✅ PASS | `test_tools.py` será criado antes de refatorar a ferramenta. |
| P04: Zero Hardcoding | ✅ PASS | Caminho `data_storage` / `logs` virá do `config_manager.py`. |
| P05: Soberania do Dado | ✅ PASS | Implementação da criptografia simétrica na fila executiva (Art. V). |

**Resultado**: APROVADO — prosseguir com planejamento.

## Technical Decisions

### Decisão 1: Fallback do Logger
- **Escolhido**: Se o Redis falhar, salvar no `config.shards_dir` (se existir) ou `/logs` na raiz.
- **Justificativa**: Garante retenção de erro crítico (ex: Redis offline não derruba a capacidade de auditar o erro).

### Decisão 2: Canal Executivo Unificado (Fonte da Verdade)
- **Escolhido**: O Stream `vitalia_events` (via `logger.py`) será a única fonte consultada por qualquer rotina (LLM ou código) para saber o estado do fluxo.
- **Justificativa**: Permite que o WebSocket, agentes e o usuário injetem ou extraiam contexto sem acoplamento e sem consultar instâncias em memória. 
- **Detalhe do Maxlen**: O `MAXLEN 50000` descarta as mensagens mais velhas (evita crash de RAM). Contudo, isso apaga rastros antigos. Portanto, não é um meio de matar o processo, apenas gestão de memória.

### Decisão 3: Criptografia da Fila Executiva (Artigo V)
- **Escolhido**: Uso da biblioteca `cryptography` (módulo Fernet) em `logger.py`. A chave de criptografia será derivada de forma determinística da variável `HMAC_MASTER_SECRET` já presente no `.env`.
- **Justificativa**: O barramento Redis ou os arquivos de fallback armazenarão a carga útil (payload) cifrada (`gAAAAA...`). Apenas componentes do projeto que possuem acesso à chave mestra no `.env` (usuários ou processos autorizados) conseguirão instanciar o logger para decriptar a mensagem. 

### Decisão 4: Mecanismo de Terminação Anti-Loop
- **Escolhido**: Injetar no System Prompt do Arquiteto (ou Engenheiro) uma regra clara para emitir um payload de Erro Fatal + a flag `__VITALIA_ABORT__`. Se `main.py` detectar a exata string `__VITALIA_ABORT__` (via `TextMentionTermination`), o GroupChat morre e retorna o log final.
- **Justificativa**: Substituímos o genérico `TERMINATE` nativo do AutoGen por `__VITALIA_ABORT__` para eliminar completamente o risco de colisão. O LLM jamais escreveria "VITALIA_ABORT" por acidente numa conversa, o que garante que a parada seja sempre um comando de sistema explícito e intencional.

### Decisão 4: Teste E2E (save_code_to_rag)
- **Escolhido**: `test_tools.py` acionará o Postgres local real.
- **Justificativa**: Valida se a infraestrutura está hígida (tabelas existem, extensões pgvector carregadas). O teste criará um vetor fake, fará assert do sucesso, e no `teardown`, executará `DELETE FROM code_vectors WHERE filepath = 'test_rag.py'`.

## Project Structure

### Documentation
- `specs/001-observability-enhancement/spec.md`
- `specs/001-observability-enhancement/checklists/requirements.md`
- `specs/001-observability-enhancement/plan.md`

### Source Code
- `vitalia-core/logger.py` [MODIFY]
- `vitalia-core/main.py` [MODIFY]
- `vitalia-core/tools.py` [MODIFY]
- `vitalia-core/tests/test_tools.py` [NEW]
- `.gitignore` [MODIFY]

## Phase Overview

### Phase 1: Setup & TDD
- Criar a suíte de testes `test_tools.py`.
- Escrever o teste para `save_code_to_rag` (verificando integridade no DB e no Redis).

### Phase 2: Foundational (Logger & Criptografia)
- Atualizar `.env` e adicionar a biblioteca `cryptography` aos requirements se necessário.
- Atualizar `logger.py` implementando criptografia AES (Fernet) baseada na `HMAC_MASTER_SECRET` para os payloads, e descriptografia transparente na leitura.
- Atualizar `logger.py` com a lógica de fallback robusto para `data_storage`/`logs`.
- Adicionar `/logs` ao `.gitignore`.

### Phase 3: Tool Instrumentation
- Fazer a refatoração de `save_code_to_rag` implementando logs verbosos (Redis, PG, Ollama). O teste da Phase 1 deve continuar passando (Green phase).

### Phase 4: Orchestrator Polish (Anti-Loop)
- Modificar `main.py` para emitir logs da URL sendo chamada pelo LLM e injetar a regra de interrupção (Anti-Loop/`__VITALIA_ABORT__`) no system prompt dos agentes.
