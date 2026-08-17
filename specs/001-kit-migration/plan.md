# Implementation Plan: Migração do Orquestrador para o Kit v0.4.0

**Branch**: `001-kit-migration` | **Date**: 24-07-2026 | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/agente-local-v2/specs/001-kit-migration/spec.md)

## Summary
Adequação do código-fonte do orquestrador (`vitalia-core`) para consumir as estruturas de pastas e os metadados (TOML) exigidos pelo Vitalia Kit v0.4.0.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: `pathlib`, `tomllib`, `redis`
**Storage**: Redis (`vitalia:workflow:plan`), JSON Fallback (`.vitalia/pipeline.json`)
**Project Type**: System Refactoring

## Constitution Check
| Princípio | Status | Observação |
|-----------|--------|------------|
| P05: Extensibilidade | ✅ PASS | O parse do TOML nativo garantirá compatibilidade com futuras extensões do Kit |

## Technical Decisions
1. **ConfigManager Dinâmico (Opção 1B)**: O uso de `pathlib.Path(__file__)` evita dívida técnica e paths hardcoded.
2. **Parsing Nativo de TOML (Opção 2B)**: Filtra metadados e envia apenas o `prompt` ao contexto do LLM.
3. **Redis Fallback (Opção 3B)**: Escrita redundante em `.vitalia/pipeline.json` garantindo monitoramento da CLI caso o Redis caia.

## Project Structure

### Documentation (this feature)
- `specs/001-kit-migration/spec.md`
- `specs/001-kit-migration/plan.md`
- `specs/001-kit-migration/tasks.md`

### Source Code
- `vitalia-core/config_manager.py` (NOVO)
- `vitalia-core/logger.py` (MODIFICADO)
- `vitalia-core/tools.py` (MODIFICADO)

## Phase Overview
### Phase 1: ConfigManager e Resolução Dinâmica
### Phase 2: Refatoração do Fallback de Estado (Redis -> JSON)
### Phase 3: Parse Nativo de TOML para Skills Dinâmicas
