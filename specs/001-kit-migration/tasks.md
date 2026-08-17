# Tasks: Migração para o Kit v0.4.0

## Phase 1: ConfigManager e Resolução Dinâmica
- [x] T001: Criar o arquivo `vitalia-core/config_manager.py`.
- [x] T002: Implementar classe `VitaliaConfig` usando `pathlib` para resolver a raiz do projeto e expor propriedades (`memory_dir`, `skills_dir`).
- [x] T003: Modificar `vitalia-core/logger.py` para instanciar o `VitaliaConfig` e remover os caminhos hardcoded.

## Phase 2: Refatoração do Fallback de Estado (Redis -> JSON)
- [x] T004: Atualizar `tools.py -> update_sprint_state` para instanciar o `VitaliaConfig` e obter o path do `.vitalia/pipeline.json`.
- [x] T005: Adicionar lógica `try-except` na chamada do Redis. Se falhar, executar `json.dump` no disco.

## Phase 3: Parse Nativo de TOML para Skills Dinâmicas
- [x] T006: Atualizar `tools.py -> load_dynamic_skill`.
- [x] T007: Modificar a leitura do arquivo para buscar primeiramente a extensão `.toml` na pasta estipulada pelo Config.
- [x] T008: Implementar o parse nativo usando `tomllib` (Python 3.11+).
- [x] T009: Retornar exclusivamente o bloco de texto contido em `prompt` para o LLM.
