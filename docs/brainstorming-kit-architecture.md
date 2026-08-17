# 🧠 Brainstorming: Arquitetura do Kit — Onde Mora o Cérebro?
<!-- brainstorming-kit-architecture.md | Atualizado em: 23-07-2026 10:18:00(GMT-04:00) -->

## Contexto e Problema Real

O usuário identificou um problema crítico: **ao trocar o modelo selecionado no Antigravity, o comportamento do agente muda drasticamente** — porque alguns modelos lêem alguns arquivos por padrão e outros não.

A Spec v0.4.0 já tinha a intuição correta: mover o máximo do "cérebro" para o kit global, deixando os arquivos locais como ponteiros mínimos. O problema é que a implementação foi parcial e criou estado inconsistente.

---

## O que a Pesquisa Revelou (Dados Factuais)

### 1. Como o Antigravity carrega arquivos de contexto

Fontes: documentação oficial Antigravity + pesquisa web cruzada.

```
HIERARQUIA DE CARREGAMENTO (Antigravity):

1. ~/.gemini/config/          ← Global (cross-project, sempre carregado)
   ├── AGENTS.md              ← Regras globais — lido por TODOS os modelos
   └── skills/                ← Skills globais (lazy-loaded)

2. .agents/ (workspace root)  ← Local do projeto
   ├── AGENTS.md              ← Regras do projeto — sobrescreve global
   └── skills/                ← Skills do projeto (lazy-loaded)
```

**O problema de troca de modelo**: O `AGENTS.md` é **sempre carregado (eager)** independente do modelo. Mas o Antigravity não garante que o *novo modelo* vai processar o conteúdo do `AGENTS.md` com a mesma ênfase que o anterior — especialmente se o `AGENTS.md` for muito longo, o novo modelo pode "varrer" o conteúdo sem internalizar bem.

### 2. Skills: Lazy vs. Eager Loading

```
AGENTS.md  → SEMPRE carregado (eager) → afeta todos os modelos igualmente
SKILL.md   → Carregado on-demand (lazy) → só quando o skill é invocado
```

**Implicação**: Regras críticas de comportamento (como "brainstorming = modo socrático") 
no `AGENTS.md` longo têm MENOR garantia de serem respeitadas do que as mesmas regras 
dentro do `SKILL.md` que é carregado só quando o skill é ativado.

### 3. Benchmark: Tamanho do AGENTS.md vs. Performance

Dados da pesquisa (LOCA-bench + estudos internos da indústria):

| Tamanho do arquivo de contexto | Impacto na performance |
|---|---|
| Conciso (< 100 linhas) | +4% vs. baseline |
| Médio (100–300 linhas) | Neutro |
| Grande (> 300 linhas, "bola de lama") | -3% a -13% |
| Gerado por LLM (vago, aspiracional) | -3% consistente |

**Regra da indústria 2026**: "Less is more". O `AGENTS.md` mais eficaz tem regras 
**hiper-específicas** (padrões exatos de erro, restrições críticas) — não longos 
princípios gerais.

### 4. O problema raiz com troca de modelos (confirmado pela pesquisa)

> *"Because different models may have different context window capacities and reasoning 
> behaviors, switching mid-task might occasionally result in 'out-of-distribution' context 
> where the new model interprets the existing history differently."*

**Tradução**: Modelos diferentes têm "atenção" diferente sobre o mesmo contexto carregado.
Um modelo menor pode ignorar partes do `AGENTS.md` que um modelo maior teria respeitado,
e vice-versa.

**A solução da indústria**: Não tentar forçar comportamento complexo via `AGENTS.md` longo.
Usar `SKILL.md` com instruções explícitas — carregadas on-demand e com menor risco de 
diluição de atenção.

### 5. O que a Spec v0.4.0 do Kit acertou e o que errou

**Acertos** (alinhados com padrões da indústria):
- ✅ FR-003: AGENTS.md local = ponteiro mínimo (correto! "Conciseness is King")
- ✅ FR-001: Constituição em YAML (machine-readable, agnóstico de modelo)
- ✅ "Thin Client" local = tendência da indústria ("Context Offloading")

**O que faltou na v0.4.0**:
- ❌ A tabela do Smart Router foi deletada sem ir para nenhum lugar
- ❌ Nenhuma regra de comportamento foi movida para dentro dos `.toml` / `SKILL.md`
- ❌ O `AGENTS.md` local virou um ponteiro... que aponta para um YAML que não tem 
  as regras comportamentais de cada skill

---

## As 4 Opções Arquiteturais (com Trade-offs)

### Opção A — "Smart Router no Kit Global" 
**Mover a tabela de roteamento do AGENTS.md local para ~/.vitalia/kit/AGENTS.md**

```
~/.vitalia/kit/AGENTS.md      ← Smart Router (122 linhas)
.agents/AGENTS.md             ← Ponteiro mínimo (20 linhas)
```

O ponteiro local instrui o agente a ler o kit global.

| Critério | Avaliação |
|---|---|
| **Alinhamento com Spec v0.4.0** | ✅ FR-003 cumprido |
| **Problema de troca de modelo** | 🟡 Parcialmente resolvido — o AGENTS.md global ainda é grande |
| **Complexidade de implementação** | 🟢 Baixa — é o que a v0.4.0 queria fazer |
| **Risco** | 🟢 Baixo |
| **Aderência ao Artigo XXIII** | ✅ Kit agnóstico de projeto |
| **Context bloat** | 🟡 Ainda carrega 122 linhas em toda sessão |

---

### Opção B — "Comportamento nos SKILL.md" (alinhado com padrões 2026)
**Mover as regras de comportamento de cada skill para DENTRO do .toml correspondente**

```
brainstorming.toml:
  prompt: """
    ## Modo Socrático
    1. NÃO fazer perguntas sequenciais tipo formulário
    2. Apresentar panorama → opções → trade-offs como bloco único
    3. Aguardar definição antes de qualquer plano
    ...regras explícitas aqui...
  """
```

O `AGENTS.md` local vira apenas: "Você tem skills vitalia-*. Ao invocá-los, siga 
estritamente as instruções do prompt do skill."

| Critério | Avaliação |
|---|---|
| **Alinhamento com Spec v0.4.0** | ✅ Extensão natural da intent |
| **Problema de troca de modelo** | ✅ Melhor solução — skill carregado on-demand |
| **Complexidade de implementação** | 🟡 Média — requer reescrever prompts dos .toml |
| **Risco** | 🟢 Baixo |
| **Context bloat** | ✅ Mínimo — só o skill relevante é carregado |
| **Consistência entre modelos** | ✅ Alta — instrução explícita no momento do uso |

---

### Opção C — "Constituição YAML como fonte de comportamento" 
**Expandir o architect-constitution.yaml para incluir regras de comportamento de cada skill**

```yaml
skills:
  brainstorming:
    mode: "socratic"
    constraints:
      - "no_sequential_questions"
      - "present_panorama_first"
      - "wait_for_user_decision"
```

O agente lê o YAML inteiro no início de cada sessão e carrega as regras via parsing.

| Critério | Avaliação |
|---|---|
| **Alinhamento com Spec v0.4.0** | 🟡 Extensão não prevista na spec original |
| **Problema de troca de modelo** | 🟡 Depende do modelo saber parsear YAML corretamente |
| **Complexidade de implementação** | 🔴 Alta — YAML estruturado, sync-constitution.py mais complexo |
| **Risco** | 🟡 Médio — YAML mal-formado derruba tudo |
| **Machine-readable** | ✅ Máximo |
| **Aderência Artigo XII (Zero Hardcoding)** | ✅ Configuração declarativa |

---

### Opção D — "Híbrido: Kit Global + Skill Self-Contained" (Recomendação)
**Combinar A + B: Smart Router mínimo no kit global + comportamento explícito em cada .toml**

```
~/.vitalia/kit/AGENTS.md (30 linhas):
  - "Você é o agente Vitalia."
  - "Ao invocar qualquer skill vitalia-*, siga estritamente o prompt do skill."
  - "Leia architect-constitution.yaml para regras de processo e segurança."

.agents/AGENTS.md (10 linhas):
  - Ponteiro para ~/.vitalia/kit/AGENTS.md

brainstorming.toml (prompt expandido, 80 linhas):
  - Todas as regras de comportamento socrático explícitas e não-ambíguas
  - Não mais referência morta a "core/brainstorming"
```

| Critério | Avaliação |
|---|---|
| **Alinhamento com Spec v0.4.0** | ✅ Completa a intent da spec |
| **Problema de troca de modelo** | ✅ Melhor proteção possível |
| **Complexidade de implementação** | 🟡 Média |
| **Context bloat** | ✅ Mínimo no AGENTS.md, rico nos skills on-demand |
| **Portabilidade** | ✅ Kit funciona igual em qualquer IDE/modelo |
| **Artigo XXIII (Agnóstico de Path)** | ✅ |

---

## Resumo Comparativo

| | A | B | C | **D** |
|---|---|---|---|---|
| Resolve troca de modelo | 🟡 | ✅ | 🟡 | ✅ |
| Alinha com Spec v0.4.0 | ✅ | ✅ | 🟡 | ✅ |
| Context bloat mínimo | 🟡 | ✅ | 🔴 | ✅ |
| Complexidade de impl. | 🟢 | 🟡 | 🔴 | 🟡 |
| Robustez cross-model | 🟡 | ✅ | 🟡 | ✅ |
| Aderência padrões 2026 | 🟡 | ✅ | ✅ | ✅ |

---

## Próximas Perguntas Antes de Qualquer Código

1. **Escopo imediato**: Quer corrigir APENAS o brainstorming agora (para validar a 
   abordagem), ou mapear TODOS os .toml que precisam de enriquecimento antes de começar?

2. **O kit-v0.3.0** vai continuar no projeto ou pode ser removido após validar que 
   tudo funciona?

3. **O `spec.md.template`** previsto na v0.4.0 ainda é prioridade, ou ficamos nos 
   bugs ativos primeiro?

4. **Há outras IDEs além do Antigravity** sendo usadas com este kit (Gemini CLI, 
   Claude Code, Cursor)? Isso define se precisamos de integração multi-IDE.
