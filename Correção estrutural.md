<--- Correção estrutural.md | 13-08-2026 09:57(GMT-04:00) -->

# Correção Estrutural — Guard Rails de Grounding v2

> **Contexto**: A Feature 006 (grounding-guard-rails) modificou 7 arquivos `.toml`.
> Três apresentaram regressões de comportamento identificadas em `/vitalia-debug`.
> Este documento registra causa raiz, contratos comportamentais e plano de ação.

---

## 1. Causa Raiz — Análise Definitiva

### 1.1 Erro Categorial: Prompts não são arquivos de configuração

A causa raiz não foi um erro de posicionamento de texto. Foi um **erro de categoria**.

Arquivos de configuração podem ser modificados aditivamente: o efeito de uma inserção é local e previsível. Arquivos `.toml` do kit são **especificações de comportamento probabilístico**. Cada palavra afeta a interpretação de todas as outras — por ordem de leitura, por peso de atenção, por ancoragem semântica.

O modelo lê o prompt de cima para baixo. O que encontra primeiro ancora o que interpreta depois. Inserir conteúdo no início de um prompt não adiciona uma instrução — **substitui o contexto de interpretação de todo o resto**.

**Consequência direta**: ao inserir `<grounding_rules>` antes de `## User Input`, o modelo recebe proibições antes de ler o pedido do usuário. Ao inserir `## Passo 0` antes de `## Comportamento`, o modelo recebe instrução de agir antes de ler que deve fazer uma pausa socrática. A âncora de atenção foi substituída silenciosamente.

### 1.2 Erro de Decomposição: operação de texto, não engenharia de comportamento

```
DECOMPOSIÇÃO ERRADA:
encontrar ponto de inserção → inserir bloco → verificar presença (grep) → próximo arquivo

DECOMPOSIÇÃO CORRETA:
descrever comportamento atual → definir comportamento desejado →
projetar modificação mínima que preserva o primeiro e adiciona o segundo →
verificar comportamentalmente → implementar → checkpoint HITL → próximo arquivo
```

A validação usada foi **estrutural** ("o bloco está presente?") em vez de **comportamental** ("o modelo produziria o mesmo output para o mesmo input de antes?").

### 1.3 Erro de Pressão: 7 arquivos sem HITL intermediário

O erro do primeiro arquivo (`brainstorming.toml`) propagou-se com o mesmo padrão defeituoso para os seguintes, pois não havia checkpoint de validação comportamental entre eles.

### 1.4 Erro de Classificação: Guardrail de Conteúdo vs. Guardrail de Comportamento

| Tipo | Definição | Exemplo |
|---|---|---|
| **Guardrail de Conteúdo** | Instrui *o que dizer* | "nunca afirme versões sem pesquisar" |
| **Guardrail de Comportamento** | Instrui *como agir* | "faça perguntas antes de produzir output" |

O `<grounding_rules>` é um guardrail de **conteúdo**. Foi inserido em posição que interferiu com guardrails de **comportamento** já existentes — especialmente a pausa socrática do brainstorming.

### 1.5 Erro de Omissão: a pergunta que nunca foi feita

> **"O modelo ainda faz a pausa socrática?"**

Inserir `## Passo 0` com instruções como "identifique", "liste", "busque" **antes** de `## Comportamento` transforma uma pausa reflexiva em uma sequência de ações imediatas. O modelo interpreta o `## Passo 0` como a primeira coisa a fazer. A pausa foi eliminada sem que a pergunta fosse formulada.

---

## 2. Verificação: `research.md` existe no fluxo do `spec-plan`?

**Resposta: SIM — existia antes da modificação.**

Evidências no `spec-plan.toml` original:

1. **`description`** (linha 1): `"Gera plan.md + research.md + constitution check"`
2. **`[context].writes`**: `"specs/*/research.md"` declarado como output previsto
3. **`[variables].output`**: `"research_file"` — variável de saída já existia
4. **Passo 4 do prompt**: template de `research.md` com o campo `"Verificado em": [URL]` — **minha modificação tentou adicionar `verified_at` que já existia com nome diferente**

**Conclusão**: o Passo 4 já cobria a necessidade de verificação. A modificação tentou adicionar algo já existente, com posicionamento errado. O arquivo precisava de ajuste de posição, não de conteúdo novo.

---

## 3. Status por Arquivo

### 3.1 Arquivos que precisam de correção

| Arquivo | Severidade | Natureza do problema |
|---|---|---|
| `brainstorming.toml` | �� CRÍTICO | Pausa socrática eliminada; `Passo 0` como ação imediata; `Rastro de Pesquisa` induz conclusão prematura; falso frontmatter YAML no meio do prompt |
| `spec-specify.toml` | 🟡 MÉDIO | `<grounding_rules>` antes de `## User Input` — âncora semântica invertida |
| `spec-plan.toml` | 🟡 MÉDIO | `<grounding_rules>` antes de `## User Input`; `verified_at` duplicou campo já existente |

### 3.2 Arquivos corretos — manter intocados

| Arquivo | Status | Justificativa |
|---|---|---|
| `spec-tasks.toml` | ✅ | Phase 0 é aditiva no template de saída |
| `spec-implement.toml` | ✅ | Passo 4 expandido com item `0.` — aditivo |
| `session-end.toml` | ✅ | Seção 1.1 após aprovação — condicional |
| `session-consolidate.toml` | ✅ | Passo 3.5 com bypass condicional |

---

## 4. Contratos Comportamentais (pré-condição obrigatória para cada modificação)

### 4.1 Contrato: `brainstorming.toml`

**O que o usuário observa (comportamento correto — antes da quebra):**
- Invoca `/vitalia-brainstorming [tema]`
- Recebe análise socrática com pontos cegos, trade-offs e consequências
- **Não recebe código, plano imediato nem output de pesquisa**
- O agente faz perguntas e aguarda resposta
- Somente após o ciclo completo, produz um plano

**Propriedades que DEVEM ser preservadas:**
1. O agente não produz output executável na primeira resposta
2. O agente apresenta trade-offs antes de qualquer decisão
3. O agente aguarda resposta do usuário antes de avançar
4. A primeira resposta é uma análise, não uma execução

**Comportamento desejado após a modificação:**
- O agente verifica internamente os domínios antes de formular as perguntas — sem mostrar esse processo
- Afirmações nos trade-offs são baseadas em fontes verificadas
- Rastro de Pesquisa é um **arquivo separado** (`research-brainstorming.md`) com link — nunca seção embutida na primeira resposta
- A pausa socrática é preservada integralmente

**Design de posicionamento:**
- `<grounding_rules>` vai no **FINAL** do prompt, depois de `## Exemplos`
- Nota interna discreta dentro de `## Comportamento`: *"Antes de formular as perguntas, verificar internamente afirmações sobre domínios externos"*
- Rastro de Pesquisa: arquivo separado com link no output final do ciclo

**Critério de validação comportamental:**
> Input: `/vitalia-brainstorming mudar banco de dados para MongoDB`
> - Modelo lê User Input + Comportamento → âncora: pausa socrática ✅
> - `<grounding_rules>` no final → lembrete de verificar afirmações, não muda o que faz primeiro ✅
> - Sem instrução de output imediato → nenhuma conclusão prematura ✅
> - **Pergunta crítica respondida: o modelo ainda faz a pausa socrática? SIM ✅**

---

### 4.2 Contrato: `spec-specify.toml`

**O que o usuário observa (comportamento correto):**
- Invoca `/vitalia-spec-specify [descrição]`
- O agente executa os 9 passos em sequência
- Produz `spec.md`, `checklists/requirements.md`, atualiza `feature.json`
- Entrega relatório de conclusão

**Propriedades que DEVEM ser preservadas:**
1. Passo 1 interpreta o input do usuário — nenhuma restrição antecede isso
2. Fluxo de 9 passos executa em ordem, sem passos extras antes do Passo 1
3. Seção `## Suposições Verificadas` já existe no Passo 5 — não será duplicada

**Comportamento desejado:** regras de grounding aplicadas durante o Passo 5 apenas.

**Design de posicionamento:** `<grounding_rules>` embutido dentro do **Passo 5** como subcondição de `## Suposições Verificadas`.

**Critério de validação comportamental:**
> Input: `/vitalia-spec-specify autenticação JWT com refresh tokens`
> - Modelo lê User Input primeiro ✅
> - Executa Passo 1 e 2 normalmente ✅
> - No Passo 5, `<grounding_rules>` restringem afirmações sobre JWT ✅
> - Fluxo de 9 passos idêntico ao original ✅

---

### 4.3 Contrato: `spec-plan.toml`

**O que o usuário observa (comportamento correto):**
- Invoca `/vitalia-spec-plan`
- Lê `spec.md` aprovado, executa Constitution Check
- Pesquisa técnica com decisões documentadas (já incluía `research.md`)
- Produz `plan.md` + artefatos auxiliares

**Propriedades que DEVEM ser preservadas:**
1. Passo 1 verifica hooks — nenhuma restrição antecede isso
2. Passo 4 já exigia `"Verificado em"` com URL — não duplicar
3. `research.md` já era output declarado — não tratar como adição nova

**Comportamento desejado:** Passo 4 reforçado com `<grounding_rules>` como protocolo de sua própria fase.

**Design de posicionamento:** `<grounding_rules>` embutido dentro do **Passo 4**, como reforço do aviso `⚠️` existente, sem duplicar o campo `"Verificado em"`.

**Critério de validação comportamental:**
> Input: `/vitalia-spec-plan`
> - Modelo executa Passo 1 (hooks) normalmente ✅
> - No Passo 4, `<grounding_rules>` reforçam o que já estava lá ✅
> - `research.md` gerado conforme template existente ✅
> - Nenhum comportamento anterior alterado ✅

---

## 5. Regras Estruturais Permanentes para Modificação de Workflows

**Regra 1 — Cross-cutting concerns vão no FINAL**
Guardrails de conteúdo vão após as instruções de comportamento e após os exemplos. O modelo deve primeiro entender contexto e comportamento esperado.

**Regra 2 — Nenhum "Passo 0" antes do Passo 1 original sem redesenho completo e aprovado**
Se verificação prévia é necessária, ela entra como nota interna dentro do Passo 1 existente — nunca como passo independente numerado.

**Regra 3 — Instruções de output só onde já há output**
Se o workflow termina com uma pergunta ou pausa, o rastro de pesquisa vai como arquivo separado com link — nunca embutido onde deveria haver uma pergunta.

**Regra 4 — Um arquivo por checkpoint HITL**
Nunca modificar mais de um arquivo `.toml` entre checkpoints de revisão.

**Regra 5 — Classificar o tipo antes de inserir**
Antes de qualquer inserção: classificar como guardrail de conteúdo ou de comportamento. Verificar conflito com instruções existentes do mesmo tipo. A pergunta é "que contrato estou honrando?", não "onde coloco o bloco?".

---

## 6. Plano Completo de Ação

### Sequência com checkpoints HITL (um arquivo por vez)

```
FASE A — brainstorming.toml (CRÍTICO — redesign)
  1. Apresentar diff proposto ao André
  2. Aguardar aprovação explícita
  3. Implementar
  4. Simular em prosa: "/vitalia-brainstorming mudar banco para MongoDB"
  5. Responder: "o modelo ainda faz a pausa socrática?" (deve ser SIM)
  6. Commit isolado

FASE B — spec-specify.toml (MÉDIO — ajuste cirúrgico)
  Mesmo fluxo | Input de simulação: "/vitalia-spec-specify autenticação JWT"

FASE C — spec-plan.toml (MÉDIO — ajuste cirúrgico)
  Mesmo fluxo | Input de simulação: "/vitalia-spec-plan"

FASE D — Validação sistêmica
  Ler os 3 arquivos em sequência
  Confirmar que nenhuma fase introduziu nova regressão cruzada
```

---

### FASE A — Design proposto: `brainstorming.toml`

| Posição | Operação | Conteúdo |
|---|---|---|
| Bloco `## Passo 0` atual | **REMOVE** | eliminado integralmente |
| Falso frontmatter `---` + `description:` | **REMOVE** | eliminado |
| Bloco `## Rastro de Pesquisa` atual | **REMOVE** | substituído por arquivo separado |
| Dentro de `## Comportamento`, como nota após item 4 | **ADD** | `⚠️ Antes de formular as perguntas: verificar internamente afirmações sobre domínios externos. Esse processo não é apresentado ao usuário — as perguntas devem ter premissas verificadas.` |
| Após `## Exemplos`, no final do prompt | **ADD** | bloco `<grounding_rules>` completo |
| Após `## Exemplos`, como instrução de ciclo completo | **ADD** | `Quando o ciclo produzir um plano final: gerar 'research-brainstorming.md' com Rastro de Pesquisa e incluir link no output final.` |

**O que NÃO muda:** pausa socrática, ausência de output imediato, estrutura de perguntas com trade-offs, instrução de aguardar resposta, `## Propósito`, `## Comportamento`, `## Exemplos`.

> **Adição confirmada pelo André (13-08-2026):** ao final do ciclo de brainstorming — após o usuário ter tomado as decisões e o agente ter produzido o plano — o workflow deve indicar explicitamente que qualquer alteração de código **deve respeitar e iniciar o pipeline SDD**:
> `Próximo passo: /vitalia-spec-specify [descrição da decisão tomada]`
> Essa instrução aparece no output final do ciclo, não na primeira resposta.

---

### FASE B — Design proposto: `spec-specify.toml`

| Posição | Operação | Conteúdo |
|---|---|---|
| Posição atual (antes de `## User Input`) | **REMOVE** | bloco `<grounding_rules>` removido |
| Dentro do **Passo 5**, como subcondição de `## Suposições Verificadas` | **ADD** | `<grounding_rules>` como protocolo de preenchimento dessa seção |

**O que NÃO muda:** fluxo de 9 passos, posição de User Input, Pre-Execution Checks, todos os outros passos.

---

### FASE C — Design proposto: `spec-plan.toml`

| Posição | Operação | Conteúdo |
|---|---|---|
| Posição atual (antes de `## User Input`) | **REMOVE** | bloco `<grounding_rules>` removido |
| Dentro do **Passo 4**, reforçando o aviso `⚠️` existente | **ADD** | `<grounding_rules>` sem duplicar o campo `"Verificado em"` |

**O que NÃO muda:** todos os passos 1-3 e 5-7, template do `research.md`, campo `"Verificado em"` existente.

---

> **Status**: Aguardando aprovação do André para iniciar FASE A.
> **Compromisso**: nenhuma linha de código será alterada antes da autorização explícita por fase.
