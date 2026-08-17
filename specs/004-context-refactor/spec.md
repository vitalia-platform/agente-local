# Especificação de Funcionalidade: Context Refactor — JSONL, Semáforo e Correção de Workflows de Sessão

**Spec ID:** SPEC-004  
**Data:** 30-07-2026  
**Autor/Agente:** Antigravity (Claude Sonnet 4.6) + André  
**Preset:** software  
**Status:** 🟡 Em Revisão  

> **Origem:** Brainstorming estruturado de 30-07-2026. Todas as 11 decisões de design fechadas.

---

## 1. Contexto e Objetivo (O Quê e Por Quê)

### Problema

O sistema de gestão de contexto distribuído do Vitalia Kit (Spec 3.1) possui três classes de problemas que comprometem a confiabilidade em ambientes multi-máquina:

1. **Formato de dados frágil:** `DECISIONS.md`, `LEARNINGS.md` e `SESSION_HISTORY.md` são arquivos Markdown usados simultaneamente como *dado* e *apresentação*. Isso torna o parse dependente de regex frágil, impossibilita deduplicação algorítmica e gera conflitos Git quando duas máquinas fazem append concorrente.

2. **Responsabilidades incorretas nos workflows:** O `session-end` escreve diretamente nos arquivos raiz do repositório de contexto, quebrando a separação de responsabilidade: somente o `session-consolidate` deveria tocar esses arquivos. O `session-start` usa instrução condicional que modelos de linguagem ignoram quando os arquivos já existem, pulando a sincronização com o repositório remoto.

3. **Ausência de controle de concorrência:** Não há mecanismo que impeça duas máquinas de consolidar o contexto simultaneamente, o que pode resultar em perda de dados ou conflitos irrecuperáveis no repositório Git de contexto.

### Objetivo

Refatorar o subsistema de memória de sessão do Vitalia Kit para:
- Separar *dado* (JSONL/YAML) de *apresentação* (Markdown gerado)
- Corrigir as responsabilidades dos workflows `session-start`, `session-end` e `session-consolidate`
- Introduzir controle de concorrência via semáforo no `DASHBOARD.md`
- Migrar o histórico existente sem perda de dados

### Escopo do Piloto

Esta spec é implementada como **piloto no projeto local** (`agente-local-v2`) via symlink para o kit global (`~/.vitalia/kit/`). Mudanças no kit se propagam automaticamente ao projeto via symlink.

---

## 2. Requisitos Funcionais

### FR-001 — Formato de Dados JSONL (MUST)
O sistema DEVE usar arquivos JSONL como fonte da verdade para entradas de `learnings`, `decisions` e `session_history`. Cada linha DEVE ser um objeto JSON com o schema:
```
{ "id", "ts", "ts_confidence", "machine", "machine_id", "category", "content" }
```
onde `id = sha256(content_128_chars + category)`, `ts` em ISO 8601 com offset de fuso.

### FR-002 — Shards YAML como Ponteiros (MUST)
Cada máquina DEVE manter um shard exclusivo em `shards/<machine_id>.yaml` contendo apenas: `machine`, `machine_id`, `last_sync`, `status`, `task`, `p0`. O shard NÃO DEVE conter entradas inline de learnings ou decisions.

### FR-003 — Arquivo `machines.json` (MUST)
O sistema DEVE manter um registro de máquinas conhecidas em `data/machines.json` com upsert por `machine_id`, registrando `name`, `first_seen` e `last_seen`.

### FR-004 — Views Markdown Geradas (MUST)
`LEARNINGS.md`, `DECISIONS.md` e `SESSION_HISTORY.md` DEVEM ser gerados automaticamente pelo `vitalia_context_engine.py` a partir dos arquivos JSONL. Esses arquivos NUNCA devem ser editados manualmente.

### FR-005 — DASHBOARD.md Separado do README.md (MUST)
O sistema DEVE manter `DASHBOARD.md` como arquivo gerado contendo: status do semáforo, topologia de máquinas (gráfico Mermaid), tabela de máquinas com staleness badge (⚠️ se > 24h). O `README.md` DEVE ser um manual estático explicativo com link para `DASHBOARD.md`.

### FR-006 — Semáforo de Consolidação no DASHBOARD.md (MUST)
O `DASHBOARD.md` DEVE conter uma seção de semáforo com: status (`LIVRE` | `LOCKED`), machine_id responsável, timestamp de início e timestamp de expiração (TTL de 10 minutos). Uma máquina que encontrar o semáforo `LOCKED` dentro do TTL DEVE interromper e exibir aviso ao usuário.

### FR-007 — `session-end` Escreve Apenas no Shard (MUST)
O workflow `session-end` DEVE escrever exclusivamente em:
- `shards/<machine_id>.yaml` (sobrescrita)
- `data/machines.json` (upsert)
- `data/session_history.jsonl` (append de entrada da sessão)

O `session-end` NÃO DEVE tocar em `SESSION_STATE.md`, `LEARNINGS.md`, `DECISIONS.md` ou `DASHBOARD.md` na raiz.

### FR-008 — `session-consolidate` com git pull --rebase (MUST)
O workflow `session-consolidate` DEVE executar `git pull --rebase` antes de qualquer operação de escrita. Em caso de conflito, DEVE interromper e instruir o usuário a resolver manualmente.

### FR-009 — `session-consolidate` com Análise LLM de DECISIONS (MUST)
O workflow `session-consolidate` DEVE incluir um passo final onde o LLM analisa as entradas novas de `data/decisions.jsonl` (detectadas por id ausente na view atual) e faz append apenas das entradas novas, preservando todo o histórico anterior.

### FR-010 — `session-start` com Instrução Imperativa (MUST)
O workflow `session-start` DEVE sempre invocar o motor de contexto para sincronização, independente de os arquivos já existirem. Bifurcação:
- Se `data/` não existe → `--action init`
- Se `data/` existe → `--action consolidate`
Em ambos os casos, o agente lê os arquivos gerados para apresentar o estado ao usuário.

### FR-011 — git push HITL com Fallback Documentado (SHOULD)
Em caso de falha por autenticação no push, o sistema DEVE exibir o comando exato para execução manual e documentar configuração de SSH/PAT no `README.md`.

### FR-012 — Migração de Histórico Legado sem Perda (MUST)
O motor DEVE implementar `--action migrate` que converte `.md` legados para JSONL com `ts_confidence: "estimated"` e `machine_id: "pre-migration"`. Arquivos legados são renomeados para `.md.bak` após migração validada.

### FR-013 — `SESSION_STATE.md` Derivado de Shards e Data (MUST)
`SESSION_STATE.md` DEVE ser gerado pelo script derivando o P0 global a partir dos shards ativos e de `data/`. É snapshot para leitura rápida; não é fonte da verdade.

### FR-014 — Convenção `.vitalia/pipeline.json` Documentada (SHOULD)
O kit DEVE documentar no `MANUAL.md` que `.vitalia/` é diretório de convenção fixa. Projetos com path customizado DEVEM usar symlink `.vitalia/ → <custom_dir>`.

### FR-015 — `install-project.sh` Cria Estrutura JSONL (MUST)
O script de instalação DEVE criar `memory/session/data/` com JSONL vazios e `machines.json`. NÃO DEVE criar `SESSION_STATE.md`, `LEARNINGS.md` ou `DECISIONS.md` diretamente.

---

## 3. Requisitos Não-Funcionais

- **NF-001 (Compatibilidade Git):** Append em JSONL resulta em diffs de uma linha. Máquinas distintas escrevendo em seus shards não geram conflitos.
- **NF-002 (Idempotência):** `--action init` e `--action consolidate` são idempotentes.
- **NF-003 (Auditabilidade):** Toda entrada JSONL é rastreável por `machine_id + ts + id`. Entradas migradas identificáveis por `ts_confidence: "estimated"`.
- **NF-004 (Semáforo TTL):** Semáforo expira após 10 minutos para evitar deadlock.
- **NF-005 (Agnóstico de Modelo):** Workflows `.toml` funcionam com qualquer LLM sem depender de capacidades avançadas de raciocínio.

---

## 4. Histórias de Usuário

**US-001** — Como desenvolvedor trabalhando em múltiplas máquinas, eu quero que o contexto do projeto seja sincronizado automaticamente via GitHub ao encerrar e iniciar sessões, para que eu nunca perca o estado de onde parei.

**US-002** — Como desenvolvedor, eu quero que o sistema impeça duas máquinas de consolidar o contexto simultaneamente, para evitar conflitos irrecuperáveis no repositório Git.

**US-003** — Como desenvolvedor, eu quero que o push falho por autenticação resulte em instruções exatas para execução manual, para que a sincronia não bloqueie meu trabalho.

**US-004** — Como desenvolvedor, eu quero visualizar no GitHub o `DASHBOARD.md` com o estado de todas as máquinas e o semáforo, para ter visibilidade do projeto em tempo real.

**US-005** — Como usuário do kit em um projeto novo, eu quero que o `/session-start` funcione corretamente mesmo sem histórico anterior, para que não haja comportamento instável.

---

## 5. Critérios de Aceite (Acceptance Scenarios)

### SC-001 — session-end não contamina a raiz
**Dado que** o usuário executa `/session-end`,  
**Quando** o workflow conclui,  
**Então** apenas `shards/<machine_id>.yaml`, `data/machines.json` e `data/session_history.jsonl` foram alterados; `LEARNINGS.md`, `DECISIONS.md` e `SESSION_STATE.md` na raiz NÃO foram modificados.

### SC-002 — session-consolidate com repositório desatualizado
**Dado que** outra máquina fez push de um novo shard antes desta sessão,  
**Quando** o usuário executa `/session-consolidate`,  
**Então** o sistema executa `git pull --rebase` com sucesso e inclui o shard da outra máquina no `DASHBOARD.md`.

### SC-003 — Semáforo bloqueia consolidação simultânea
**Dado que** a Máquina A está com semáforo `LOCKED` no remoto (dentro do TTL),  
**Quando** a Máquina B executa `/session-consolidate` e faz `git pull`,  
**Então** a Máquina B detecta o semáforo ativo, exibe aviso e interrompe.

### SC-004 — Semáforo expirado permite retomada
**Dado que** o semáforo está `LOCKED` mas o TTL já expirou (> 10 min),  
**Quando** qualquer máquina executa `/session-consolidate`,  
**Então** o sistema ignora o semáforo expirado e prossegue normalmente.

### SC-005 — session-start em projeto novo
**Dado que** o projeto não possui `data/` nem arquivos de contexto,  
**Quando** o usuário executa `/session-start`,  
**Então** o motor executa `--action init`, cria `data/` com JSONL vazios, e apresenta "Nenhum contexto anterior encontrado" sem erros.

### SC-006 — session-start com contexto existente
**Dado que** o projeto possui `data/` com entradas JSONL e shards,  
**Quando** o usuário executa `/session-start`,  
**Então** o motor executa `--action consolidate`, regera as views, e o agente apresenta P0 e últimos aprendizados.

### SC-007 — Deduplicação de entradas JSONL
**Dado que** `data/learnings.jsonl` já contém entrada com id `abc123`,  
**Quando** o `session-consolidate` processa shard com entrada cujo id é `abc123`,  
**Então** a entrada NÃO é duplicada e o log exibe "1 entrada ignorada (já presente)".

### SC-008 — Migração legada sem perda
**Dado que** o repositório de contexto possui `LEARNINGS.md` e `DECISIONS.md` legados,  
**Quando** o motor executa `--action migrate`,  
**Então** todas as entradas são convertidas para JSONL com sentinels de migração, os `.md` originais renomeados para `.md.bak`, e as views regeradas.

### SC-009 — Push falho por autenticação
**Dado que** o repositório remoto requer autenticação sem chave SSH configurada,  
**Quando** o `session-consolidate` tenta `git push origin main` e recebe erro de autenticação,  
**Então** o sistema exibe o comando exato para execução manual e mantém o commit local pronto.

---

## 6. Fora do Escopo

- Sincronização via Redis (previsto para v0.6+)
- Rotação automática de JSONL
- Resolução automática de conflitos Git
- Interface visual web para o Dashboard
- Variável `{{VITALIA_DIR}}` nos `.toml` (Convenção B — documentada)
- Correção de paths `.specify/` legados (tarefa separada, Fase 1)

---

## 7. Dependências e Suposições

### Dependências
- `~/.vitalia/kit/scripts/vitalia_context_engine.py` — será refatorado
- `.vitalia/memory/session/` como sub-repositório Git com remote configurado
- Python 3.8+ com `hashlib`, `json`, `yaml` (PyYAML), `glob`, `subprocess`

### Suposições
- `machine_id = sha256(hostname)[:8]`
- Repositório de contexto remoto usa branch `main`
- O agente tem acesso a `run_command` para executar o script Python

---

## 8. Entidades de Dados

| Entidade | Formato | Localização | Responsável por escrever |
|---|---|---|---|
| Shard da máquina | YAML | `shards/<machine_id>.yaml` | `session-end` |
| Registro de máquinas | JSON | `data/machines.json` | `session-end` |
| Aprendizados | JSONL | `data/learnings.jsonl` | `session-consolidate` |
| Decisões | JSONL | `data/decisions.jsonl` | `session-consolidate` |
| Histórico de sessões | JSONL | `data/session_history.jsonl` | `session-end` |
| View Learnings | Markdown gerado | `LEARNINGS.md` | `vitalia_context_engine.py` |
| View Decisions | Markdown gerado | `DECISIONS.md` | `vitalia_context_engine.py` |
| View Histórico | Markdown gerado | `SESSION_HISTORY.md` | `vitalia_context_engine.py` |
| Estado global | Markdown gerado | `SESSION_STATE.md` | `vitalia_context_engine.py` |
| Dashboard visual | Markdown gerado | `DASHBOARD.md` | `vitalia_context_engine.py` |
| Manual de referência | Markdown estático | `README.md` | Manual (por versão do kit) |
