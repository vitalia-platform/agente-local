# Tasks: Context Refactor — JSONL, Semáforo e Correção de Workflows

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Gerado em**: 30-07-2026  

---

<!--
=======================================================================
GUARD RAILS — LEIA ANTES DE EXECUTAR QUALQUER TASK
=======================================================================

<tool_rules>
REGRA 1 — AMBIENTE VIRTUAL (OBRIGATÓRIO):
  NUNCA execute python, python3 ou pip fora do ambiente virtual.
  A Phase 0 localiza e ativa o venv. Sem venv ativo = PARAR e reportar.

REGRA 2 — CONHECIMENTO INTERNO PROIBIDO para:
  - Versões ou capacidades de modelos LLM (Gemini, Claude, GPT, etc.)
  - Versões de bibliotecas externas (PyYAML, etc.)
  - Comportamento de APIs externas
  → DEVE executar search_web em sites oficiais ANTES de afirmar.
  → Se sem resultado: declare "não encontrei fonte — aguardando input".

REGRA 3 — TASKS SÃO GATES:
  NUNCA marque uma task [x] sem ter executado o comando/ação correspondente
  e verificado o output. "Parece correto" não é suficiente.

REGRA 4 — CITATION CONTRACT:
  Toda afirmação sobre sistema externo nesta sessão cita a fonte:
  "Fonte verificada: [URL ou arquivo lido nesta sessão]"

REGRA 5 — ERROS SÃO BLOQUEANTES:
  Se um comando retornar exit code != 0: PARAR, reportar ao usuário,
  aguardar instrução. Não prosseguir para a próxima task.
</tool_rules>
=======================================================================
-->

---

## MVP Scope

> Implementar **Phase 1 + Phase 2 + Phase 3 + Phase 4** entrega o sistema funcional completo.
> Phase 5 (Documentação) é incremento obrigatório para encerramento da feature.

---

## Phase 0: Verificação de Ambiente (PRÉ-REQUISITO ABSOLUTO)

*Deve ser executada ANTES de qualquer outra task. Sem aprovação desta phase, nenhuma outra inicia.*

- [x] T000-A Localizar ambiente virtual do projeto: `find . -name "activate" -path "*/bin/activate" 2>/dev/null | grep -v ".vitalia" | head -5`
- [x] T000-B [P] Se venv encontrado: ativar e registrar o path exato. Se não encontrado: reportar ao usuário e aguardar instrução — NÃO prosseguir.
- [x] T000-C [P] Verificar versão do Python ativo no venv: `python3 --version` — confirmar >= 3.8
- [x] T000-D Verificar se PyYAML já está instalado no venv: `python3 -c "import yaml; print(yaml.__version__)"` — se ausente, registrar como pendente para T001
- [x] T000-E [P] Verificar se git está disponível: `git --version` — confirmar presença
- [x] T000-F [P] Verificar se o sub-repositório de contexto tem remote configurado: `git -C .vitalia/memory/session remote -v` — se ausente: reportar e aguardar instrução

---

## Phase 1: Setup

*Pré-requisitos e estrutura de diretórios. Sem label de US. Requer Phase 0 completa.*

- [x] T001 Verificar e instalar PyYAML **no venv ativo** (somente se T000-D indicou ausente): `pip install pyyaml` e registrar em `requirements.txt` do kit se ausente

- [x] T002 Criar estrutura `data/` no repositório de contexto: `mkdir -p .vitalia/memory/session/data/`
- [x] T003 [P] Inicializar `data/learnings.jsonl` vazio (arquivo vazio, não `null`)
- [x] T004 [P] Inicializar `data/decisions.jsonl` vazio
- [x] T005 [P] Inicializar `data/session_history.jsonl` vazio
- [x] T006 [P] Inicializar `data/machines.json` com estrutura base: `{"machines": {}}`

---

## Phase 2: Foundational — Context Engine

*Refatoração do script Python (kit global). Sem label de US. Bloqueia todas as phases seguintes.*

- [x] T007 Criar backup do `vitalia_context_engine.py` atual: `cp ~/.vitalia/kit/scripts/vitalia_context_engine.py ~/.vitalia/kit/scripts/vitalia_context_engine.py.bak`
- [x] T008 Implementar função `generate_id(category, content)` em `vitalia_context_engine.py`: `sha256(f"{category}{content[:128]}".encode()).hexdigest()[:16]`
- [x] T009 [P] Implementar função `get_machine_id()` em `vitalia_context_engine.py`: `sha256(socket.gethostname().encode()).hexdigest()[:8]`
- [x] T010 [P] Implementar função `get_machine_name()` em `vitalia_context_engine.py`: lê `socket.gethostname()`
- [x] T011 Implementar função `read_jsonl(filepath)` → lista de dicts, retorna `[]` se arquivo vazio/ausente
- [x] T012 Implementar função `append_jsonl(filepath, entry_dict)` → adiciona uma linha JSON ao arquivo JSONL
- [x] T013 Implementar função `read_shard_yaml(filepath)` → dict, retorna `{}` se ausente
- [x] T014 Implementar função `write_shard_yaml(filepath, data_dict)` → escreve YAML com PyYAML
- [x] T015 Implementar função `upsert_machines_json(session_dir, machine_id, name)` → atualiza `data/machines.json`
- [x] T016 Implementar função `check_semaphore(session_dir)` → retorna `(is_locked, machine_id, expires_at)` lendo seção do `DASHBOARD.md`
- [x] T017 Implementar função `set_semaphore(session_dir, status, machine_id)` → reescreve seção de semáforo no `DASHBOARD.md`
- [x] T018 Implementar função `generate_dashboard(session_dir, shards, machines)` → gera `DASHBOARD.md` completo com semáforo + Mermaid + tabela
- [x] T019 Implementar função `generate_session_state(session_dir, shards)` → gera `SESSION_STATE.md` derivado de shards + data/
- [x] T020 Implementar função `generate_view_md(session_dir, jsonl_filename, output_filename, title)` → gera view Markdown de JSONL com header timestamp
- [x] T021 Implementar `--action init` em `vitalia_context_engine.py`: cria `data/` + JSONL vazios + `machines.json`; idempotente
- [x] T022 Implementar `--action consolidate` em `vitalia_context_engine.py`:
  - Lê todos os shards YAML em `shards/`
  - Checa semáforo (aborta se LOCKED dentro TTL)
  - Adquire semáforo (LOCKED)
  - Gera `DASHBOARD.md`, `SESSION_STATE.md`
  - Regera views `LEARNINGS.md`, `DECISIONS.md`, `SESSION_HISTORY.md`
  - Libera semáforo (LIVRE) antes de retornar
- [x] T023 Implementar `--action migrate` em `vitalia_context_engine.py`:
  - Parse de `LEARNINGS.md` legado → entradas com `ts_confidence: "estimated"`, `machine_id: "pre-migration"`
  - Parse de `DECISIONS.md` legado → idem
  - Parse de `SESSION_HISTORY.md` legado → idem
  - Deduplicação por `id` antes de gravar
  - Renomeia `.md` → `.md.bak` após validação
  - Migra `shards/*.md` → `shards/*.yaml`
  - Regera todas as views
- [x] T024 Escrever testes de validação de idempotência: executar `--action consolidate` 2x sem novas entradas e verificar que JSONL não cresceu

---

## Phase 3: User Story 1 — Sincronização Multi-Máquina no Session-End

**Story Goal**: Ao encerrar uma sessão, apenas o shard e o histórico local são atualizados; arquivos raiz do repositório de contexto ficam intocados.  
**Independent Test**: SC-001 — `git diff` não mostra alterações em `LEARNINGS.md`, `DECISIONS.md`, `SESSION_STATE.md` após `session-end`.  
**Referência**: FR-002, FR-003, FR-007, FR-013

- [x] T025 [US1] Reescrever prompt do `session-end.toml` (~/.vitalia/kit/extensions/session-end.toml):
  - Fase 1 (Reflexão HITL): mantida — LLM extrai aprendizados e decisões da sessão
  - Fase 2 (CORRIGIDA): escreve SOMENTE em `shards/<machine_id>.yaml` (YAML ponteiro) — remove instrução de escrever em SESSION_STATE/LEARNINGS/DECISIONS raiz
  - Fase 2 adicional: upsert em `data/machines.json`
  - Fase 2 adicional: append em `data/session_history.jsonl` (uma entrada da sessão)
  - Fase 3: commit do repositório raiz (código)
  - Fase 4: shard local atualizado — exibe instrução para `/session-consolidate`
- [x] T026 [US1] Validar SC-001: executar session-end e verificar via `git -C .vitalia/memory/session diff` que arquivos raiz não foram alterados

---

## Phase 4: User Story 2 — Consolidação Multi-Máquina com Semáforo

**Story Goal**: Ao consolidar, o sistema sincroniza com a nuvem, processa todos os shards e garante exclusividade de acesso.  
**Independent Test**: SC-002, SC-003, SC-004 — verificação de pull, lock e expiração.  
**Referência**: FR-001, FR-004, FR-005, FR-006, FR-008, FR-009, FR-011

- [x] T027 [US2] Reescrever prompt do `session-consolidate.toml` (~/.vitalia/kit/extensions/session-consolidate.toml) com 8 passos:
  - Passo 1: `git -C .vitalia/memory/session pull --rebase` — aborta em conflito com mensagem HITL
  - Passo 2: `vitalia_context_engine.py --action consolidate` — checa semáforo, adquire lock
  - Passo 3: LLM analisa entradas novas em `data/learnings.jsonl` (por id ausente na view) → exibe ao usuário
  - Passo 4: LLM analisa entradas novas em `data/decisions.jsonl` → merge inteligente, preserva histórico
  - Passo 5: Atualiza `SESSION_HISTORY.md` com entradas novas
  - Passo 6: `git -C .vitalia/memory/session add . && git commit -m "chore: session consolidated by <machine_id>"`
  - Passo 7: `git -C .vitalia/memory/session push origin main` — em falha de auth: exibe HITL com comando manual
  - Passo 8: Confirma "✅ Contexto sincronizado na nuvem" ou estado pendente
- [x] T028 [P] [US2] Validar SC-002: simular shard de outra máquina e confirmar que consolidate o inclui no DASHBOARD.md
- [x] T029 [P] [US2] Validar SC-003: injetar semáforo LOCKED manualmente no DASHBOARD.md e confirmar que consolidate aborta
- [x] T030 [US2] Validar SC-004: injetar semáforo com `expires_at` no passado e confirmar que consolidate prossegue
- [x] T031 [US2] Validar SC-007: inserir entrada duplicada em shard e confirmar que deduplicação por `id` funciona
- [x] T032 [US2] Validar SC-009: simular falha de auth no push e confirmar mensagem HITL exata

---

## Phase 5: User Story 3 — Session-Start Determinístico

**Story Goal**: Session-start funciona corretamente em projetos novos e existentes, sempre invocando o motor de contexto.  
**Independent Test**: SC-005 (novo), SC-006 (existente).  
**Referência**: FR-010

- [x] T033 [US3] Corrigir prompt do `session-start.toml` (~/.vitalia/kit/extensions/session-start.toml):
  - Passo 1 (CORRIGIDO): instrução imperativa — "Sempre invoque o motor de contexto. Se `data/` não existir: `--action init`. Se existir: `--action consolidate`."
  - Substituir a instrução condicional "Se a estrutura não existir..."
  - Manter Passos 2-4 intactos
- [x] T034 [US3] Validar SC-005: remover `data/` e executar session-start; confirmar que `init` é chamado
- [x] T035 [US3] Validar SC-006: com `data/` existente, executar session-start; confirmar que `consolidate` é chamado e P0 apresentado

---

## Phase 6: User Story 4 — Migração do Histórico Existente

**Story Goal**: Todo o histórico legado em Markdown é migrado para JSONL sem perda de dados.  
**Independent Test**: SC-008 — contar entradas no `.md` original vs linhas no `.jsonl` gerado.  
**Referência**: FR-012

- [x] T036 [US4] Executar migração no repositório de contexto do projeto piloto:
  `python3 .vitalia/scripts/vitalia_context_engine.py --action migrate --session-dir .vitalia/memory/session`
- [x] T037 [US4] Validar SC-008: contar entradas em `LEARNINGS.md.bak` vs linhas em `data/learnings.jsonl`; confirmar `ts_confidence: "estimated"` e `machine_id: "pre-migration"`
- [x] T038 [US4] Inspecionar views geradas (`LEARNINGS.md`, `DECISIONS.md`) e confirmar que o conteúdo é equivalente ao original

---

## Phase 7: Polish & Cross-Cutting

*Regras always-on, documentação e conformidade. Sem label de US.*

- [x] T039 Atualizar `rules/always-on/session-context.md` (~/.vitalia/kit/rules/always-on/session-context.md):
  - Adicionar regra imperativa de execução do engine no session-start
  - Atualizar tabela de responsabilidades (quem escreve o quê)
  - Adicionar regra de imutabilidade JSONL
  - Corrigir paths `.specify/memory/session/` → `.vitalia/memory/session/`
- [x] T040 Reescrever `README.md` do repositório de contexto (`.vitalia/memory/session/README.md`) como manual estático (Opção C+D):
  - Seções estáticas: Visão Geral, Arquitetura dos Arquivos, Protocolo do Semáforo, Configuração SSH/PAT, FAQ, Erros Conhecidos
  - Seções dinâmicas: Versão do Kit, Máquinas registradas, Changelog do README
  - Link para `DASHBOARD.md`
- [x] T041 [P] Atualizar `install-project.sh` para criar `memory/session/data/` com JSONL vazios + `machines.json` em instalações novas
- [x] T042 [P] Adicionar convenção `.vitalia/pipeline.json` ao `MANUAL.md` (~/.vitalia/kit/MANUAL.md): `.vitalia/` como path fixo (Convenção B)
- [x] T043 Commit e push de todos os arquivos de documentação: `git add . && git commit -m "docs(004): context refactor documentation"`
- [x] T044 Commit no repositório de contexto pós-migração: `git -C .vitalia/memory/session add . && git commit -m "chore: migrate context to JSONL v0.5 — SPEC-004"`
- [x] T045 Push do repositório de contexto e confirmar que DASHBOARD.md está legível no GitHub

---

## Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Context Engine — Foundational)
    ↓               ↓               ↓              ↓
Phase 3 (US1)  Phase 4 (US2)  Phase 5 (US3)  Phase 6 (US4)
    ↓               ↓               ↓              ↓
Phase 7 (Polish & Cross-Cutting)
```

## Parallel Execution

Tasks marcadas `[P]` dentro da mesma fase podem ser executadas simultaneamente:

- **Phase 1**: T003, T004, T005, T006 (arquivos independentes)
- **Phase 2**: T009, T010 podem iniciar junto com T008; T013, T014 junto com T011, T012
- **Phase 3 & 4**: US1 e US2 são fases paralelas (workflows independentes)
- **Phase 5**: US3 é independente de US1 e US2 no nível de arquivo (session-start.toml ≠ session-end.toml)
- **Phase 7**: T041, T042 são paralelas entre si

---

## FR Coverage

| FR | Descrição resumida | Tasks |
|---|---|---|
| FR-001 (JSONL) | Fonte da verdade JSONL | T008, T011, T012, T023 |
| FR-002 (Shard YAML) | Ponteiro por máquina | T013, T014, T025 |
| FR-003 (machines.json) | Registry de máquinas | T015, T025 |
| FR-004 (Views geradas) | .md gerado do JSONL | T020, T022 |
| FR-005 (DASHBOARD separado) | DASHBOARD.md + README manual | T018, T040 |
| FR-006 (Semáforo) | Lock + TTL | T016, T017, T018, T027 |
| FR-007 (session-end somente shard) | Responsabilidade correta | T025, T026 |
| FR-008 (git pull --rebase) | Sync antes de consolidar | T027 |
| FR-009 (LLM merge decisions) | Análise inteligente | T027 |
| FR-010 (session-start imperativo) | Instrução determinística | T033, T034, T035 |
| FR-011 (push HITL) | Fallback de autenticação | T027, T032 |
| FR-012 (migração legada) | Opção D com sentinels | T023, T036, T037, T038 |
| FR-013 (SESSION_STATE derivado) | Gerado de shards+data | T019, T022 |
| FR-014 (Convenção pipeline.json) | Documentação Convenção B | T042 |
| FR-015 (install-project.sh) | Estrutura JSONL no install | T041 |
