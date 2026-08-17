<!-- plan.md | 12-08-2026 21:10(GMT-04:00) -->

# Implementation Plan: Grounding Guard Rails v2

**Branch:** `006-grounding-guard-rails`
**Date:** 12-08-2026
**Spec:** [spec.md](./spec.md)
**Research:** [research.md](./research.md)

---

## Summary

Implementar o sistema de Grounding Guard Rails v2 para o Vitalia Kit — um conjunto de
arquivos de configuração, regras always-on e modificações pontuais em 7 workflows e 1 script
Python que obrigam os agentes LLM a verificar afirmações factuais sobre domínios externos,
rastrear as fontes em tabelas auditáveis e permitir que novos domínios sejam curados
interativamente pelo desenvolvedor via session-consolidate.

A abordagem é **aditiva e non-breaking**: novos arquivos são criados; workflows recebem blocos
novos (Passo 0 + grounding_rules + Rastro de Pesquisa); o context engine recebe nova função
e extensões às existentes — sem alterar o comportamento atual de learnings/decisions.

---

## Technical Context

**Language/Version:** Python 3.x (compatível com a versão já usada no vitalia_context_engine.py)
**Primary Dependencies:** PyYAML (já presente), json (stdlib), hashlib (stdlib)
**Storage:** Arquivos de texto (YAML, JSONL, Markdown) — sem banco de dados
**Testing:** Validação manual via Acceptance Scenarios (AS-001..AS-006)
**Target Platform:** Developer Tooling (local + kit global compartilhado)
**Project Type:** Kit extension (configuration + workflow + script)
**Performance Goals:** Sem SLA de tempo — operação offline/local
**Constraints:**
- `grounding.md` (always-on) DEVE ter ≤ 60 linhas
- Modificações nos .toml são aditivas — não quebrar comportamento existente
- `grounding-domains-local.yaml` nunca é editado manualmente (always generated)

---

## Constitution Check

| Princípio | Status | Observação |
|---|---|---|
| Art. I — SDD Pipeline | ✅ PASS | Seguindo pipeline completo |
| Art. II — Decomposição Atômica | ✅ PASS | Tasks serão atômicas no tasks.md |
| Art. III — Test-First | ✅ PASS | Validação via AS-xxx; lógica Python com fallback testável |
| Art. IV — Impacto Holístico | ✅ PASS | Sem PII, sem saúde, sem multi-tenancy |
| Art. V — Soberania do Dado | ✅ PASS | Nenhum dado de saúde ou PII |
| Art. VI — Segredos no Git | ✅ PASS | Nenhuma credencial. JSONL: apenas metadados de domínio |
| Art. VII — Segurança de API | ✅ PASS | N/A — sem API pública |
| Art. VIII/IX — HITL Gate Saúde | ✅ PASS | Preset software — nenhum gate acionado |
| Art. XII — Zero Hardcoding | ✅ PASS | Caminhos via variável; domínios via YAML configurável |
| Art. XIV — YAGNI | ✅ PASS | 2 novos arquivos; modificações pontuais nos existentes |
| Art. XV — Timestamp | ✅ PASS | Todos os arquivos gerados terão timestamp correto |
| Art. XVII — Ambiente Reprodutível | ✅ PASS | Feature melhora este artigo (Phase 0 + pip check) |
| Art. XVIII — Observabilidade | ✅ PASS | Feature é expansão deste artigo |
| Art. XXIII — Kit Agnóstico de Path | ✅ PASS | Editamos via symlinks do projeto |

**Resultado:** ✅ APROVADO

---

## Technical Decisions

Ver [research.md](./research.md) para justificativas detalhadas. Sumário:

| Decisão | Escolha |
|---|---|
| Formato domínios global | YAML (grounding-domains.yaml) |
| Localização global | ~/.vitalia/kit/config/ |
| Override local | JSONL append-only → yaml gerado pelo consolidate |
| Curadoria HITL | ask_question 2 rodadas (global → local/rejeitar) |
| Bloco de enforcement | XML `<grounding_rules>` embutido no prompt de cada .toml |
| Funções Python modificadas | generate_grounding_yaml() nova + 3 funções existentes |

---

## Project Structure

### Documentation (esta feature)
```
specs/006-grounding-guard-rails/
├── spec.md
├── plan.md                ← este arquivo
├── research.md
├── tasks.md               (gerado por /vitalia-spec-tasks)
└── checklists/
    └── requirements.md
```

### Arquivos Novos
```
~/.vitalia/kit/config/
└── grounding-domains.yaml         [NOVO] Domínios globais, editável por humanos

~/.vitalia/kit/rules/always-on/
└── grounding.md                   [NOVO] Regra always-on ≤ 60 linhas

.vitalia/memory/session/data/
└── grounding-domains.jsonl        [NOVO] Append-only, criado pelo init_context()

.vitalia/memory/session/
└── grounding-domains-local.yaml   [NOVO] VIEW gerada pelo consolidate — não editar
```

### Arquivos Modificados
```
~/.vitalia/kit/extensions/
├── brainstorming.toml             [MOD] Passo 0 + <grounding_rules> + Rastro
├── spec-specify.toml              [MOD] Passo 0 + <grounding_rules> + Suposições Verificadas
├── spec-plan.toml                 [MOD] Passo 0 + <grounding_rules> + Rastro no research.md
├── spec-tasks.toml                [MOD] Phase 0 (T000-A..T000-E) automática
├── spec-implement.toml            [MOD] Passo 4 expandido (venv + pip check + compat)
├── session-end.toml               [MOD] Fase 1: registro scope:null no JSONL
└── session-consolidate.toml       [MOD] Passo 3.5: curadoria HITL com ask_question

~/.vitalia/kit/scripts/
└── vitalia_context_engine.py      [MOD] +generate_grounding_yaml(), +consolidate, +dashboard, +init

~/.vitalia/kit/rules/always-on/
└── architect-constitution.md      [MOD] Artigo XVIII: +1 linha ponteiro para grounding.md
```

---

## Phase Overview

### Phase 1: Fundação (Novos arquivos — sem tocar nos workflows)

**Objetivo:** Criar a infraestrutura base. Nenhum workflow existente é alterado nesta fase.

1.1 Criar diretório `~/.vitalia/kit/config/`
1.2 Criar `grounding-domains.yaml` com 7 domínios + fontes verificadas + exempt_domains
1.3 Criar `grounding.md` (always-on) — protocolo + domínios resumidos + template Rastro + XML proibições
1.4 Validar: `grounding.md` tem ≤ 60 linhas
1.5 Modificar `vitalia_context_engine.py`:
    - Adicionar `generate_grounding_yaml()` (merge global + JSONL)
    - Modificar `consolidate_context()` para chamar a nova função
    - Modificar `generate_dashboard()` para adicionar seção Guard Rails
    - Modificar `init_context()` para criar o JSONL vazio e yaml inicial
1.6 Validar `init_context()` localmente: JSONL criado, yaml local com base global
1.7 Adicionar 1 linha no Artigo XVIII da Constituição

### Phase 2: Brainstorming e Specify (Maior impacto imediato)

**Objetivo:** Cobrir as fases onde o problema foi observado pela primeira vez.

2.1 Modificar `brainstorming.toml`:
    - Novo Passo 0: identificar domínios presentes no pedido
    - Bloco `<grounding_rules>` no topo do prompt
    - Seção Rastro de Pesquisa obrigatória ao final do output
2.2 Modificar `spec-specify.toml`:
    - Bloco `<grounding_rules>` no Passo 4
    - Seção obrigatória `## Suposições Verificadas` na spec gerada
    - Gate: menção a tecnologia/API → requer fonte ou tag [NEEDS VERIFICATION]
2.3 Validar com sessão de brainstorming real (AS-001, AS-002)

### Phase 3: Plan e Tasks (Completar cobertura de planning)

**Objetivo:** Cobrir as fases de planejamento técnico.

3.1 Modificar `spec-plan.toml`:
    - Bloco `<grounding_rules>` no Passo 4 (Pesquisa Técnica)
    - Formato do `research.md` inclui coluna `verified_at` e URL
    - Proibição explícita: "Escolhido: X porque é mais moderno" sem fonte
3.2 Modificar `spec-tasks.toml`:
    - Gerar Phase 0 (T000-A a T000-E) automaticamente em todo tasks.md gerado
    - Ordem correta: T000-A (ativar venv) → T000-B (python --version do venv)
3.3 Validar Phase 0 no tasks.md (AS-003)

### Phase 4: Implement, Session-End e Dashboard (Fechar o ciclo)

**Objetivo:** Cobrir a execução e o ciclo de retroalimentação.

4.1 Modificar `spec-implement.toml`:
    - Expandir Passo 4 (setup) com: venv, python do venv, pip check, compat de libs novas
4.2 Modificar `session-end.toml`:
    - Na Fase 1 (Reflexão), após aprendizados [KIT]: detectar novos domínios de risco
    - Se aprovado pelo usuário: append scope:null no JSONL
4.3 Modificar `session-consolidate.toml`:
    - Adicionar Passo 3.5: leitura do JSONL, tabela de curadoria, ask_question 2 rodadas,
      append scope_decision, HITL duplo para promoção global
4.4 Validar ciclo completo (AS-004, AS-005, AS-006)

### Phase 5: Documentação e Governança

**Objetivo:** Deixar rastro e garantir consistência.

5.1 Criar `grounding-domains-local.yaml` inicial no repo de sessão do projeto
5.2 Commitar no repo de sessão (memory/session)
5.3 Atualizar `BRAINSTORMING_GROUNDING_ARCHITECTURE.md` com status real da auditoria
5.4 Testar fluxo completo end-to-end com sessão real

---

## Rastro de Pesquisa — Este Documento

**Gerado em:** 12-08-2026 21:10(GMT-04:00)
**Domínios verificados:** python_packages, external_apis (infraestrutura do kit)

| # | Afirmação feita | Verificado? | Fonte consultada | Data |
|---|---|---|---|---|
| 1 | PyYAML já é dependência do context engine | Sim | grep "import yaml" vitalia_context_engine.py:9 | 12-08-2026 |
| 2 | config/ não existe ainda no kit | Sim | ls ~/.vitalia/kit/config/ → inexistente | 12-08-2026 |
| 3 | session-consolidate tem 7 passos atuais (Passo 8 é o final) | Sim | leitura de session-consolidate.toml | 12-08-2026 |
| 4 | vitalia_context_engine.py tem 383 linhas | Sim | wc -l no script | 12-08-2026 |
