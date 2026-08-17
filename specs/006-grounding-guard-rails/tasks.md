<!-- tasks.md | 12-08-2026 21:15(GMT-04:00) -->

# Tasks: Grounding Guard Rails v2

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Gerado em**: 12-08-2026 21:15(GMT-04:00)

---

## MVP Scope

> Implementar **Phase 1 + Phase 2 + Phase 3** entrega o núcleo funcional:
> domínios configuráveis, regra always-on ativa e rastro de pesquisa nos artefatos principais.
> Phase 4 completa o ciclo de retroalimentação. Phase 5 é governança e polish.

---

## Phase 0: Grounding & Environment (desta própria feature)

*Nota: esta feature é tooling puro (YAML/TOML/Markdown/Python) — sem venv Python de projeto.
 Verificações aplicáveis ao script vitalia_context_engine.py.*

- [X] T000-A Confirmar Python disponível: `python3 --version`
- [X] T000-B Confirmar PyYAML instalado: `python3 -c "import yaml; print(yaml.__version__)"`
- [X] T000-C Confirmar que `~/.vitalia/kit/config/` NÃO existe ainda (evitar sobrescrever)
- [X] T000-D Confirmar que `grounding.md` NÃO existe em `~/.vitalia/kit/rules/always-on/`

---

## Phase 1: Fundação

*Criar arquivos base sem tocar nos workflows existentes. Sem label de US — deps compartilhadas.*

- [X] T001 Criar diretório `~/.vitalia/kit/config/`
- [X] T002 [P] Criar `~/.vitalia/kit/config/grounding-domains.yaml` com 7 domínios, fontes verificadas e exempt_domains conforme plano
- [X] T003 [P] Criar `~/.vitalia/kit/rules/always-on/grounding.md` (≤ 60 linhas) com: protocolo 4 passos, domínios resumidos, template Rastro, bloco `<grounding_rules>` XML
- [X] T004 Validar que `grounding.md` tem ≤ 60 linhas: `wc -l ~/.vitalia/kit/rules/always-on/grounding.md`
- [X] T005 Adicionar 1 linha ponteiro no Artigo XVIII de `~/.vitalia/kit/rules/always-on/architect-constitution.md`: `Ver regra grounding.md — protocolo completo`
- [X] T006 Modificar `vitalia_context_engine.py` — adicionar função `generate_grounding_yaml(session_dir)`:
      lê grounding-domains.jsonl + global yaml → merge → gera grounding-domains-local.yaml
      com campos: base_version, local_entries, last_generated, domains, exempt_domains
- [X] T007 Modificar `vitalia_context_engine.py` — `consolidate_context()`:
      chamar `generate_grounding_yaml(session_dir)` após as views existentes
- [X] T008 Modificar `vitalia_context_engine.py` — `generate_dashboard()`:
      adicionar seção "## Guard Rails de Grounding" com tabela: arquivo global (status),
      yaml local (status + data + link), contagem de pendentes (⚠️ se > 0)
- [X] T009 Modificar `vitalia_context_engine.py` — `init_context()`:
      criar `data/grounding-domains.jsonl` vazio se não existir;
      criar `grounding-domains-local.yaml` inicial (cópia da base global) se não existir
- [X] T010 Validar Phase 1: rodar `python3 vitalia_context_engine.py --action init` no repo de sessão do projeto
      → confirmar que grounding-domains.jsonl e grounding-domains-local.yaml foram criados
- [X] T011 Validar `generate_dashboard()`: rodar `--action consolidate`
      → confirmar seção "Guard Rails de Grounding" aparece no DASHBOARD.md com "✅ 0 pendentes"

---

## Phase 2: Brainstorming e Specify

*Cobertura das fases onde o problema foi observado pela primeira vez.*

**Story Goal**: Brainstorming e Specify produzem artefatos com rastro de pesquisa verificável.
**Independent Test**: AS-001 (brainstorming Django) e AS-002 (item NAO VERIFICADO).
**Referência**: FR-002, FR-005, FR-006

- [X] T012 [US2] Modificar `~/.vitalia/kit/extensions/brainstorming.toml` — adicionar ao início do `prompt`:
      bloco `<grounding_rules>` XML com 4 regras negativas + referência ao grounding-domains.yaml
- [X] T013 [US2] Modificar `brainstorming.toml` — adicionar Passo 0 antes da discussão:
      "Identificar quais domínios do grounding-domains.yaml estão presentes no pedido.
       Listar afirmações que precisarão de verificação externa."
- [X] T014 [US2] Modificar `brainstorming.toml` — adicionar instrução ao final do `prompt`:
      seção obrigatória "## Rastro de Pesquisa" com tabela padronizada
- [X] T015 [US2] Modificar `~/.vitalia/kit/extensions/spec-specify.toml` — adicionar bloco `<grounding_rules>` no Passo 4
- [X] T016 [US2] Modificar `spec-specify.toml` — adicionar ao Passo 5 (geração da spec):
      seção obrigatória `## Suposições Verificadas`;
      gate: menção a tecnologia/API específica → citar fonte verificada ou marcar `[NEEDS VERIFICATION]`
- [X] T017 [US2] Validar AS-001: executar brainstorming sobre feature Django
      → confirmar Passo 0 identificou python_packages, output tem seção Rastro de Pesquisa com pypi.org
- [X] T018 [US2] Validar AS-002: confirmar que afirmação sem verificação aparece como "NAO VERIFICADO" na tabela

---

## Phase 3: Plan e Tasks

*Cobertura das fases de planejamento técnico e geração de tarefas de ambiente.*

**Story Goal**: Plan gera research.md com fontes verificadas; tasks.md tem Phase 0 automaticamente.
**Independent Test**: AS-003 (Phase 0 com ordem T000-A antes T000-B).
**Referência**: FR-006, FR-007

- [X] T019 [US2] Modificar `~/.vitalia/kit/extensions/spec-plan.toml` — adicionar bloco `<grounding_rules>` no Passo 4 (Pesquisa Técnica)
- [X] T020 [US2] Modificar `spec-plan.toml` — no Passo 4, exigir que research.md inclua campo `verified_at` com data e URL para cada decisão técnica; proibir "Escolhido X porque é mais moderno" sem fonte
- [X] T021 [P] [US3] Modificar `~/.vitalia/kit/extensions/spec-tasks.toml` — no Passo 4 (geração do tasks.md), inserir Phase 0 automática antes de Phase 1:
      T000-A: Ativar venv (`source .venv/bin/activate` ou equivalente)
      T000-B: `python --version` (agora lê o Python do venv)
      T000-C: Verificar deps vs requirements.txt
      T000-D: Verificar versão atual de libs externas mencionadas na spec em pypi.org
      T000-E: `pip check` (conflitos de compatibilidade)
- [X] T022 [US3] Validar AS-003: executar spec-tasks em qualquer feature com venv
      → confirmar T000-A é o primeiro item e T000-B é o segundo

---

## Phase 4: Implement, Session-End e Dashboard

*Fechar o ciclo de retroalimentação de domínios.*

**Story Goal**: Novos domínios descobertos em sessões chegam ao dashboard e podem ser curados.
**Independent Test**: AS-004 (curadoria), AS-005/AS-006 (dashboard pendentes/limpo).
**Referência**: FR-003, FR-004, FR-008, FR-009, FR-010, FR-011, FR-012

- [X] T023 [US3] Modificar `~/.vitalia/kit/extensions/spec-implement.toml` — expandir Passo 4 (setup de ambiente):
      1. Localizar e ativar venv antes de qualquer execução
      2. `python --version` do venv (não do sistema)
      3. Verificar versões instaladas vs requirements.txt
      4. `pip check` para detectar conflitos entre libs
      5. Para toda lib nova: pesquisar versão atual em pypi.org + verificar compatibilidade antes de adicionar ao requirements
- [X] T024 [P] [US4] Modificar `~/.vitalia/kit/extensions/session-end.toml` — na Fase 1 (Reflexão), após extração de aprendizados [KIT]:
      detectar se algum aprendizado revela domínio de risco novo ou fonte melhor;
      se aprovado pelo usuário: append em `data/grounding-domains.jsonl` com scope:null
      (campos: id, type, scope, domain, description, authoritative_sources, machine_id, timestamp, reason)
- [X] T025 [US4] Modificar `~/.vitalia/kit/extensions/session-consolidate.toml` — adicionar Passo 3.5 entre Passos 3 e 4:
      1. Ler `data/grounding-domains.jsonl`
      2. Filtrar entradas new_domain/new_source sem scope_decision correspondente
      3. Se pendentes existirem: exibir tabela markdown com: #, tipo, domínio/fonte, motivo, máquina, data
      4. Rodada A (ask_question multi-select): "Quais devem ir para o kit global?"
      5. Rodada B (ask_question multi-select): "Quais ficam apenas locais? (restante)"
      6. Não selecionados em B → scope: "rejected"
      7. Para cada decisão: append scope_decision no JSONL (type, target_id, scope, decided_by, timestamp)
      8. Para scope:"global": exibir diff do que seria adicionado ao yaml global + pedir confirmação HITL
      9. Se confirmado: editar ~/.vitalia/kit/config/grounding-domains.yaml
- [X] T026 [US5] Validar AS-004: inserir 2 entradas manuais com scope:null no JSONL
      → executar session-consolidate → confirmar tabela exibida, ask_question em 2 rodadas,
      2 scope_decision registradas no JSONL
- [X] T027 [US5] Validar AS-005: com entradas scope:null no JSONL → rodar consolidate
      → confirmar dashboard exibe "⚠️ 2 entradas aguardando curação"
- [X] T028 [US5] Validar AS-006: após curação completa → rodar consolidate
      → confirmar dashboard exibe "✅ 0 pendentes"

---

## Phase 5: Governança e Documentação

*Polish, consistência e primeira execução real end-to-end.*

- [X] T029 Criar `grounding-domains-local.yaml` inicial no repo de sessão do projeto (agente-local)
      via `python3 vitalia_context_engine.py --action init --session-dir .vitalia/memory/session`
- [X] T030 Commitar no repo de sessão: `git -C .vitalia/memory/session add . && git commit -m "feat: grounding guard rails v2 — initial domains"`
- [X] T031 Atualizar `BRAINSTORMING_GROUNDING_ARCHITECTURE.md` com status real da auditoria:
      marcar como [APLICADO] todos os guard rails efetivamente implementados
- [X] T032 Executar sessão de brainstorming real e validar que o Rastro de Pesquisa aparece
      corretamente no output do agente (teste end-to-end)

---

## Dependency Graph

```
Phase 0 (verificações)
    ↓
Phase 1 (Fundação: grounding.md + yaml + context engine)
    ↓              ↓               ↓
Phase 2         Phase 3         Phase 4
(brainstorm    (plan +         (implement +
 + specify)     tasks)          session-end +
                                consolidate)
    ↓              ↓               ↓
                Phase 5 (Governança)
```

T002 e T003 são paralelas (arquivos independentes).
T006-T009 são sequenciais (funções do mesmo script).
T012-T014 são sequenciais (mesmo arquivo, ordem de inserção importa).
T021 é paralela a T019-T020 (arquivos diferentes).
T024 e T025 são paralelas (arquivos diferentes).

## Parallel Execution

Tasks marcadas [P] dentro da mesma fase podem ser executadas simultaneamente:

| Phase | Paralelas |
|---|---|
| Phase 1 | T002 ‖ T003 |
| Phase 2 | (nenhuma — mesmo arquivo, ordem importa) |
| Phase 3 | T021 pode iniciar após T018, paralela a T019-T020 |
| Phase 4 | T024 ‖ T025 (arquivos diferentes) |

---

## FR Coverage

| FR | Descrição | Tasks |
|---|---|---|
| FR-001 | Arquivo de Domínios Global | T001, T002 |
| FR-002 | Regra Always-On | T003, T004 |
| FR-003 | JSONL Append-Only | T009, T024 |
| FR-004 | Consolidação do YAML Local | T006, T007, T010 |
| FR-005 | Rastro de Pesquisa nos Artefatos | T014, T016 |
| FR-006 | Protocolo nos Workflows | T012, T015, T019 |
| FR-007 | Phase 0 no spec-tasks | T021, T022 |
| FR-008 | Passo 0 no spec-implement | T023 |
| FR-009 | Gate de Curadoria | T025, T026 |
| FR-010 | Dashboard | T008, T027, T028 |
| FR-011 | Init do JSONL | T009, T010 |
| FR-012 | Session-End scope:null | T024 |

FRs sem cobertura: **nenhum** ✅
