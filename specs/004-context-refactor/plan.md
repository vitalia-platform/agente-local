# Implementation Plan: Context Refactor — JSONL, Semáforo e Correção de Workflows

**Branch**: `004-context-refactor`  
**Date**: 30-07-2026  
**Spec**: [spec.md](./spec.md)  
**Status**: 🟡 Aguardando aprovação

---

## Summary

Refatorar o `vitalia_context_engine.py` e os três workflows de sessão (`session-start`, `session-end`, `session-consolidate`) para separar dado (JSONL/YAML) de apresentação (Markdown gerado), introduzir semáforo de consolidação e corrigir responsabilidades incorretas. Como o projeto local usa symlink para o kit global, todas as mudanças no kit são imediatamente refletidas no piloto.

---

## Technical Context

**Language/Version**: Python 3.8+  
**Primary Dependencies**: `hashlib` (stdlib), `json` (stdlib), `yaml` (PyYAML — já instalado), `glob` (stdlib), `subprocess` (stdlib), `argparse` (stdlib)  
**Storage**: Arquivos JSONL + YAML no sub-repositório Git `.vitalia/memory/session/`  
**Testing**: Testes de integração via scripts de validação manual + checklist SC-xxx  
**Target Platform**: Server / Developer workstation (Linux/WSL2)  
**Project Type**: CLI script (kit global)  
**Performance Goals**: Operações de consolidação < 5s em repositório com < 1000 entradas JSONL  
**Constraints**: Sem dependências externas além de PyYAML; script deve rodar offline (sem rede) exceto nos passos de git push

---

## Constitution Check

| Artigo | Princípio | Status | Observação |
|---|---|---|---|
| Art. I (SDD) | Spec aprovada antes do plano | ✅ PASS | SPEC-004 criada via /vitalia-spec-specify |
| Art. II (Decomposição Atômica) | Tarefas granulares e testáveis | ✅ PASS | Cada ação do script é isolada e testável |
| Art. III (Test-First) | Lógica de negócio testada | ✅ PASS | Cada `--action` validado por SC-xxx da spec |
| Art. IV (Impacto Holístico) | Multi-tenancy, RBAC, LGPD | ✅ PASS | Feature é de infraestrutura de dev; sem dado de saúde ou PII |
| Art. V (Soberania do Dado) | Dado de saúde | ✅ PASS | Fora do escopo — feature não lida com dados clínicos |
| Art. VI (Segredos no Git) | Credenciais | ✅ PASS | Nenhuma credencial hardcoded; Git push via SSH/PAT do usuário |
| Art. XII (Zero Hardcoding) | Paths e configurações | ✅ PASS | `session_dir` via `--session-dir` argumento; `.vitalia/` como convenção documentada (Convenção B) |
| Art. XIV (YAGNI) | Mínimo necessário | ✅ PASS | Sem introduzir nova infraestrutura; PyYAML já presente |
| Art. XV (Timestamps) | Carimbo de tempo em artefatos | ✅ PASS | Todos os arquivos gerados incluirão header `<!-- atualizado em: -->` |
| Art. XX (Documentação) | README e docs atualizados | ✅ PASS | `README.md` estático do repositório de contexto e `MANUAL.md` do kit previstos na spec |
| Art. XXI (Automação) | Scripts para processos repetitivos | ✅ PASS | Toda operação via `vitalia_context_engine.py --action <x>` |

**Resultado**: ✅ APROVADO — prosseguir com planejamento

---

## Technical Decisions

### TD-001: PyYAML para shards (não `tomllib` ou JSON puro)
- **Escolhido**: PyYAML (`import yaml`)
- **Justificativa**: Shards precisam ser legíveis por humanos no GitHub; YAML é mais expressivo que JSON para esse propósito e já é dependência comum em ambientes Python de dev
- **Alternativas**:
  - JSON: rejeitado — legibilidade inferior para humanos no GitHub
  - TOML: rejeitado — `tomllib` é stdlib só no Python 3.11+; PyYAML disponível em 3.8+

### TD-002: sha256 via `hashlib` (sem dependência externa)
- **Escolhido**: `hashlib.sha256(f"{category}{content[:128]}".encode()).hexdigest()[:16]`
- **Justificativa**: 16 hex chars (64-bit) é suficiente para deduplicação em repositórios de contexto com < 100k entradas; zero chance de colisão na prática
- **Alternativas**:
  - UUID4: rejeitado — não é determinístico; não permite deduplicação
  - sha256 completo (64 chars): rejeitado — verbose demais no JSONL

### TD-003: Semáforo como seção em DASHBOARD.md (não arquivo separado)
- **Escolhido**: Seção `## 🔒 Status de Consolidação` no `DASHBOARD.md`
- **Justificativa**: Evita arquivo adicional; o DASHBOARD.md já é commitado e propagado via git push; TTL verificado por comparação de timestamps em Python (sem cron)
- **Alternativas**:
  - Arquivo `LOCK.json` separado: rejeitado — mais um arquivo a gerenciar; não agrega valor sobre embutir no DASHBOARD
  - Redis lock: rejeitado — fora do escopo desta spec (previsto para v0.6+)

### TD-004: `git pull --rebase` via `subprocess.run()`
- **Escolhido**: `subprocess.run(["git", "-C", session_dir, "pull", "--rebase"], capture_output=True)`
- **Justificativa**: Permite capturar stderr para detectar conflitos (exit code != 0) e apresentar mensagem clara ao agente/usuário
- **Alternativas**:
  - `GitPython`: rejeitado — dependência externa desnecessária
  - `os.system()`: rejeitado — não captura output para detecção de erro

### TD-005: Migração com arquivo `.md.bak` (não deleção)
- **Escolhido**: Renomear `LEARNINGS.md` → `LEARNINGS.md.bak` após migração validada
- **Justificativa**: Preserva rastreabilidade; usuário pode inspecionar manualmente os dados originais; reversível antes do push
- **Alternativas**:
  - Deletar `.md` originais: rejeitado — sem fallback em caso de bug na migração
  - Mover para `archive/`: rejeitado — complexidade desnecessária; `.bak` é convenção universal

---

## Project Structure

### Documentation (this feature)
```
specs/004-context-refactor/
├── spec.md                       ← SPEC-004 (este arquivo)
├── plan.md                       ← este documento
├── research.md                   ← embutido nas TD acima (< 5 arquivos afetados)
├── data-model.md                 ← ver seção abaixo
└── checklists/
    └── requirements.md
```

### Source Code — Arquivos Afetados
```
~/.vitalia/kit/                   ← kit global (via symlink no projeto local)
├── scripts/
│   └── vitalia_context_engine.py ← REFATORAÇÃO COMPLETA
├── extensions/
│   ├── session-start.toml        ← CORREÇÃO DE PROMPT (instrução imperativa)
│   ├── session-end.toml          ← REESCRITA DE PROMPT (somente shards)
│   └── session-consolidate.toml  ← REESCRITA COMPLETA (8 passos)
└── rules/always-on/
    └── session-context.md        ← ATUALIZAÇÃO (tabela de responsabilidades)

.vitalia/memory/session/          ← repositório de contexto (sub-repo Git)
├── data/                         ← NOVO DIRETÓRIO
│   ├── learnings.jsonl           ← NOVO (fonte da verdade)
│   ├── decisions.jsonl           ← NOVO (fonte da verdade)
│   ├── session_history.jsonl     ← NOVO (fonte da verdade)
│   └── machines.json             ← NOVO (registry de máquinas)
├── shards/
│   └── local.md → local.yaml    ← MIGRAÇÃO DE FORMATO
├── DASHBOARD.md                  ← NOVO (gerado, com semáforo)
├── SESSION_STATE.md              ← MANTIDO (gerado, derivado de shards+data/)
├── LEARNINGS.md                  ← GERADO (view de learnings.jsonl)
├── DECISIONS.md                  ← GERADO (view de decisions.jsonl)
├── SESSION_HISTORY.md            ← GERADO (view de session_history.jsonl)
└── README.md                     ← REESCRITO (manual estático + link DASHBOARD)
```

---

## Phase Overview

### Phase 1 — Setup e Estrutura (Pré-requisitos)
- Criar estrutura `data/` no repositório de contexto
- Inicializar arquivos JSONL vazios e `machines.json`
- Verificar dependência PyYAML

### Phase 2 — Migração do Histórico Legado (`--action migrate`)
- Implementar parser de `.md` legado → JSONL (Opção D: timestamp estimado + sentinel)
- Renomear `.md.bak` após validação
- Migrar `shards/local.md` → `shards/local.yaml`
- Validar views geradas contra dados de origem

### Phase 3 — Refatoração do Context Engine (`vitalia_context_engine.py`)
- Implementar `--action init` (novo: cria estrutura JSONL)
- Implementar `--action consolidate` (refatorado: lê JSONL, gera views, DASHBOARD com semáforo)
- Implementar lógica de semáforo (acquire, release, TTL check)
- Implementar deduplicação por `id` no merge de entradas
- Implementar `--action migrate`

### Phase 4 — Correção dos Workflows `.toml`
- Reescrever `session-end.toml`: somente escreve em shard YAML + session_history.jsonl
- Reescrever `session-consolidate.toml`: 8 passos com git pull --rebase, semáforo, LLM merge, git push HITL
- Corrigir `session-start.toml`: instrução imperativa com bifurcação init/consolidate
- Atualizar `session-context.md` (always-on rule): tabela de responsabilidades + regra imperativa

### Phase 5 — Documentação e Validação Final
- Reescrever `README.md` do repositório de contexto (Opção C+D: estático + FAQ)
- Validar todos os 9 SCs da spec manualmente
- Registrar aprendizados e decisões no shard local

---

## Data Model

Ver [data-model.md](./data-model.md).

---

## Quickstart (Cenário de Validação)

Ver [quickstart.md](./quickstart.md).
