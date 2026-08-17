# Análise: Gestão de Contexto entre Versões do Kit Vitalia

> [!NOTE]
> Análise baseada em leitura direta dos arquivos legados + pesquisa web em fontes primárias.
> Nenhuma suposição de conhecimento interno foi utilizada.

---

## Mapa das Versões Identificadas

| Versão | Diretório | Abordagem de Contexto | Formato de Session |
|---|---|---|---|
| **vitalia-agent-kit** | `kit-legado/vitalia-agent-kit` | CONTEXT.md simples + scripts bash | `.agent/session/` |
| **vitalia-spec** | `kit-legado/vitalia-spec` | CONTEXT.md + Shards + DASHBOARD + SESSION_HISTORY | `.specify/memory/session/` |
| **spec-agents** | `kit-legado/spec-agents` | Herdado da vitalia-spec (mesmos arquivos) | `.specify/memory/session/` |
| **kit-v0.3.0** | `kit-legado/kit-v0.3.0` | CONTEXT.md + feature.json + pipeline.json | `.vitalia/` |
| **kit-v1.0.0** | `kit-legado/kit-v1.0.0` | Idem v0.3.0 | `.vitalia/` |
| **kit atual (v0.4.0)** | `~/.vitalia/kit` | Herdado do v0.3.0, sem mudança estrutural | `.vitalia/` |

---

## Análise por Versão

### Versão 1 — `vitalia-agent-kit` (A mais simples)

**Estrutura de contexto:**
```
.agent/session/
└── CONTEXT.md          ← arquivo único, monolítico
    └── SESSION_HISTORY.md  ← log append-only
```

**Mecanismo de sincronização:** script bash `session-sync.sh` com ETag para controle de conflito.

**O que o CONTEXT.md armazena:**
- Visão geral do projeto (nome, tipo, stack, objetivo)
- Estado atual (última sessão, feature em andamento, branch)
- O que foi feito (últimas 3 sessões)
- Próximos passos por prioridade (P0, P1, P2)
- Arquitetura do projeto (diretórios, ADRs)
- Regras e constraints ativos
- Dependências externas
- **Notas e Aprendizados** ← tudo misturado

**Pontos fortes:**
- ✅ Simples e direto — um único arquivo para ler
- ✅ Humano legível, Git-nativo
- ✅ session-start claramente estruturado: valida → lê contexto → resume P0
- ✅ session-end pergunta sobre aprendizados (Passo 2: "knowledge-curator ou adr-writing")
- ✅ Confiou no humano para confirmar o que foi aprendido

**Pontos fracos:**
- ❌ Tudo misturado em um arquivo: estado ≠ decisões ≠ aprendizados
- ❌ `SESSION_HISTORY.md` cresce indefinidamente (log imutável sem rotação)
- ❌ Nenhuma separação: aprendizado do kit vs. aprendizado do projeto
- ❌ ETag para conflito é frágil (bash puro, sem lock atômico)
- ❌ Sem integração com pipeline SDD — o contexto é paralelo, não integrado

---

### Versão 2 — `vitalia-spec` (A mais complexa — pico de sofisticação)

**Estrutura de contexto:**
```
.specify/memory/session/
├── CONTEXT.md           ← estado + P0 + constraints
├── SESSION_HISTORY.md   ← log imutável, cronologia reversa
├── DASHBOARD.md         ← agregação visual dos shards
├── README.md            ← gerado por script Python
├── CONSOLIDATION_LOG.md ← controle de lock distribuído
└── shards/
    └── [MACHINE_ID].md  ← shard local de cada máquina
```

**Mecanismo de sincronização:** Lock distribuído via Git + arquivo `CONSOLIDATION_LOG.md` com estados CONSOLIDANDO/CONSOLIDADO. Pull/push atômico.

**Inovações desta versão:**
- **Multi-máquina**: cada máquina tem seu shard. `session-consolidate` agrega tudo.
- **Lock distribuído real**: se outra máquina tem o lock, o processo para.
- **session-end e session-consolidate são responsabilidades separadas**: end escreve shard local; consolidate faz push na nuvem.
- **Dashboard visual**: `generate_context_readme.py` gera README com Mermaid.
- **session-end Fase 1 — skill-evaluation**: analisa o transcript! Propõe melhorias. Escreve em `.specify/extensions/lib/` (local) ou `kit-v2/extensions/lib/` (global).

**Pontos fortes:**
- ✅ Arquitetura multi-máquina funcional (distribuída)
- ✅ Lock distribuído correto (commit + push como operação atômica)
- ✅ Separação clara de responsabilidades: end ≠ consolidate
- ✅ **Fase 1 do session-end é exatamente o loop de aprendizado que precisamos**: lê transcript → propõe melhorias → distingue escopo local vs. global
- ✅ `session-context.md` como rule always-on: "ANTES de responder qualquer coisa, leia o CONTEXT.md"
- ✅ Smart-routing como rule always-on separada

**Pontos fracos:**
- ❌ Extremamente complexa: 7 arquivos + scripts Python + bash + Git subtree
- ❌ Scripts Python dependem de infraestrutura específica (`lib_machine.py`, `lib_sync_guard.py`)
- ❌ `CONSOLIDATION_LOG.md` ainda é frágil (race condition entre verificação e commit do lock)
- ❌ CONTEXT.md ainda monolítico: estado + constraints + notas misturados
- ❌ Sem integração com SDD: contexto paralelo ao pipeline

---

### Versão 3 — `kit-v0.3.0` / `kit-v1.0.0` (Simplificação pós-vitalia-spec)

**Estrutura de contexto:**
```
.vitalia/
├── feature.json     ← feature ativa (JSON estruturado)
├── pipeline.json    ← estado do pipeline (transporte entre extensions)
└── [sem CONTEXT.md template explícito]
```

**Mudança de paradigma:** abandona o CONTEXT.md monolítico, substitui por `feature.json` para rastreamento da feature ativa e `pipeline.json` para transporte de estado entre extensions.

**Pontos fortes:**
- ✅ Dados estruturados (JSON) para estado de máquina
- ✅ Mais leve: sem scripts Python complexos
- ✅ `feature.json` mapeia 1:1 com o pipeline SDD (feature → spec → plan → tasks)
- ✅ Integração via Redis ou arquivo para transporte entre extensions

**Pontos fracos:**
- ❌ **Perdeu toda a camada de aprendizado** da vitalia-spec (skill-evaluation na Fase 1 do session-end sumiu)
- ❌ Perdeu SESSION_HISTORY.md (histórico longitudinal)
- ❌ Perdeu a separação entre estado, decisões e aprendizados
- ❌ JSON não é legível por humano (perde o valor de inspeção manual)
- ❌ session-end voltou a ser simples, sem o loop de reflexão

---

### Kit atual (v0.4.0) — O estado atual

**Herda do v0.3.0** com `feature.json` e `pipeline.json`. Sem mudança na camada de contexto.

**Problema adicional identificado:**
O `session-start.toml` ainda referencia `~/.vitalia-spec/` (caminho legado da vitalia-spec) no Passo 2:
```
Ler: ~/.vitalia-spec/rules/always-on/architect-constitution.md
Ler: ~/.vitalia-spec/AGENTS.md
```
Isso é um bug: o caminho correto agora é `~/.vitalia/kit/`. O agente que usa a versão atual está lendo de um caminho que não existe mais.

---

## O que a Pesquisa da Indústria Diz (2026)

A indústria convergiu para uma **arquitetura de três tiers**:

| Tier | Escopo | Arquivos | Característica |
|---|---|---|---|
| **Tier 0 — Working Memory** | Sessão ativa, janela de contexto | Conversation buffer | Efêmero — some no fim da sessão |
| **Tier 1 — Session State** | Progresso recente, tarefa ativa | `TASKS.md`, `sprint_atual.md`, daily logs | Semi-persistente — 3-5 sessões |
| **Tier 2 — Long-Term Memory** | Conhecimento permanente, decisões, lições | `MEMORY.md`, ADRs, `AGENTS.md` | Persistente — vive no projeto |

**Padrões confirmados por Anthropic, GitHub Copilot e pesquisas de fóruns (2026):**

1. **Git-Native Memory**: arquivos versionados como artefatos de primeira classe.
2. **Progressive Disclosure**: `< 400 tokens` por arquivo. Separar em arquivos menores.
3. **Metadata blocks**: `last_updated`, `owner`, `status` no topo de cada arquivo.
4. **Consolidação reflexiva**: agente periodicamente sumariza logs e atualiza o arquivo de long-term memory (é exatamente o que a Fase 1 do session-end da vitalia-spec fazia).
5. **Separação semântica**: regras estáticas (`AGENTS.md`) ≠ estado dinâmico (`TASKS.md`) ≠ lições aprendidas (`MEMORY.md`).

---

## Diagnóstico Comparativo

| Capacidade | agent-kit | vitalia-spec | v0.3.0/v0.4.0 | Indústria 2026 |
|---|---|---|---|---|
| Estado de sessão | ⚠️ Monolítico | ✅ Separado | ⚠️ JSON | ✅ `TASKS.md` |
| Decisões/ADRs | ⚠️ Misturado | ⚠️ Misturado | ❌ Ausente | ✅ Separado |
| Loop de aprendizado | ⚠️ Manual | ✅ Fase 1 | ❌ Perdido | ✅ Consolidação reflexiva |
| Multi-máquina | ❌ | ✅ Complexo | ❌ | ⚠️ Via Git |
| Integração SDD | ❌ | ❌ | ⚠️ Parcial | N/A |
| Escopo kit vs. projeto | ❌ | ⚠️ Fase 1 distingue | ❌ | ✅ Separado |
| Legibilidade humana | ✅ | ⚠️ Complexo | ❌ JSON | ✅ Markdown |
| Bug de caminho legado | ❌ | — | ✅ | — |

**Legenda:** ✅ Funciona bem | ⚠️ Parcial/Problemático | ❌ Ausente/Quebrado

---

## Estratégia Proposta: Arquitetura Híbrida de 3 Tiers

### Princípio de design

> Cada arquivo tem **uma responsabilidade**, **um dono**, e **uma frequência de atualização**.
> Nenhuma informação é duplicada. O agente carrega apenas o que precisa, quando precisa.

### Estrutura proposta

```
.vitalia/
├── context/
│   ├── SESSION_STATE.md     ← Tier 1: o que está ativo AGORA
│   │   "Feature ativa, branch, P0, arquivos em edição"
│   │   Atualizado por: session-start (leitura), session-end (escrita)
│   │   Tamanho máximo: 300 tokens
│   │
│   ├── DECISIONS.md         ← Tier 2: decisões arquiteturais (ADRs compactos)
│   │   "Escolhemos X porque Y. Data. Impacto."
│   │   Atualizado por: vitalia-adr, session-end (proposta)
│   │   Nunca sobrescrito — append-only
│   │
│   └── LEARNINGS.md         ← Tier 2: aprendizados da sessão
│       "O agente fez X errado / descobriu Y / o kit precisa de Z"
│       Atualizado por: session-end (Fase de Reflexão)
│       Dois tracks separados:
│         [KIT] → alimenta spec de melhoria do kit
│         [PROJETO] → alimenta backlog do projeto atual

~/.vitalia/kit/memory/
└── KIT_IMPROVEMENTS.md      ← Tier 2 global: backlog de melhorias do kit
    Alimentado por: session-end quando [KIT] learnings detectados
    Usado por: vitalia-skill-evaluation para priorizar specs do kit
```

### Como cada session workflow se comporta

**session-start:**
```
1. Ler architect-constitution.yaml (SEMPRE — governa tudo)
2. Ler smart-router.md (se roteamento implícito necessário)
3. Ler .vitalia/context/SESSION_STATE.md → apresentar P0
4. Se spec ativa: ler feature.json → mostrar tasks pendentes
5. Perguntar: "Continuar P0 ou outro foco hoje?"
```

**session-end:**
```
Fase 1 — Reflexão sobre aprendizados (CRÍTICA — não pular):
  - Ler transcript da sessão
  - Identificar: erros do agente, correções do usuário, decisões tomadas
  - Classificar cada item: [KIT] ou [PROJETO]
  - Propor: atualização de LEARNINGS.md + melhorias concretas

Fase 2 — Registro de estado:
  - Atualizar SESSION_STATE.md com P0 e status atual
  - Se decisão arquitetural: propor append em DECISIONS.md

Fase 3 — Pipeline SDD (novo):
  - Se LEARNINGS.md tem itens [KIT] aprovados:
    → Criar ou atualizar spec em specs/kit-improvements/
  - Se LEARNINGS.md tem itens [PROJETO]:
    → Criar tasks no backlog da spec ativa (ou propor nova spec)

Fase 4 — Commit local (sem push):
  - Commit de SESSION_STATE.md + DECISIONS.md + LEARNINGS.md
  - Shard local para multi-máquina (se aplicável)
```

**session-consolidate:**
```
- Responsabilidade única: push para nuvem + dashboard
- Lock distribuído simples via git commit atômico
- Sem lógica de reflexão (isso é do session-end)
```

### Resposta ao requisito da instrução "não confie em conhecimento interno"

A instrução correta para o `analyze.toml` (e demais skills de análise) seria:

```toml
# analyze.toml — Passo 1, antes de qualquer análise:

### OBRIGATÓRIO: Pesquisa de Contexto Antes da Análise

Antes de emitir qualquer diagnóstico ou recomendação:

1. **Não confie em conhecimento interno de treinamento.**
   Todo padrão, regra ou "melhor prática" que você invocar DEVE ser:
   a) Extraído diretamente de um arquivo do projeto (spec, plan, constitution, ADRs), OU
   b) Buscado via web_search em fontes primárias (documentação oficial, GitHub, papers).
   
2. **Para cada finding, cite a fonte:**
   "Fonte: architect-constitution.yaml, Artigo I" OU "Fonte: github.com/spec-kit"
   
3. **Se a fonte não existir**, marque o finding como [REQUER VALIDAÇÃO] e
   sugira ao usuário verificar manualmente antes de agir.
```

Isso deveria ser um **artigo da Constituição** (Artigo sobre Epistemologia do Agente), não apenas uma instrução de prompt — para que se aplique a todos os skills, não apenas ao analyze.

---

## Resumo da Recomendação

| Elemento | De onde vem | Decisão |
|---|---|---|
| SESSION_STATE.md | Melhor do agent-kit (simplicidade) | ✅ Adotar |
| DECISIONS.md separado | Padrão da indústria 2026 | ✅ Novo |
| LEARNINGS.md com dois tracks [KIT]/[PROJETO] | Fase 1 da vitalia-spec + indústria | ✅ Novo |
| Loop de reflexão no session-end | vitalia-spec Fase 1 (era a melhor feature) | ✅ Recuperar |
| session-end ≠ session-consolidate | vitalia-spec (responsabilidades separadas) | ✅ Manter |
| feature.json para pipeline SDD | v0.3.0 | ✅ Manter |
| Lock distribuído para multi-máquina | vitalia-spec (mas simplificado) | ⚠️ Opcional |
| Instrução "não confie em conhecimento interno" | Artigo da Constituição | ✅ Novo |

> [!IMPORTANT]
> A Área 3 do Épico (Arquitetura de Memória de Sessão) deve **recuperar o loop de reflexão** da vitalia-spec, mas com a separação de escopos [KIT] vs [PROJETO] que nunca existiu em nenhuma versão anterior.
> Esse loop fechado é o mecanismo de auto-melhoria do kit.
