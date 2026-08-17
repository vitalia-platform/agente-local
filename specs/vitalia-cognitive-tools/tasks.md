# Tasks: Ferramentas Cognitivas

## Phase 1: Ferramenta de Audit
- [x] T001: Implementar `query_audit_log(limit=5)` chamando `r.xrevrange("vitalia:events", "+", "-", count=limit)`.
- [x] T002: Realizar parse condicional (try-except) buscando os jsons onde `type == "llm_turn"`.

## Phase 2: Memória de Curto Prazo
- [x] T003: Criar ferramenta `read_working_memory` que faz um GET limpo nas chaves Redis `vitalia:hot_rag:*`.

## Phase 3: Sistema Dinâmico de Skills
- [x] T004: Adicionar função `load_dynamic_skill` que verifica o path relativo em `../../.specify/skills` e carrega o arquivo `SKILL.md`.
