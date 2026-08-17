<!-- research.md | 12-08-2026 21:09(GMT-04:00) -->

# Technical Research: Grounding Guard Rails v2

**Feature:** `006-grounding-guard-rails`
**Data:** 12-08-2026

---

## Decisão 1: Formato do Arquivo de Domínios Global

**Problema:** Como representar os domínios de grounding de forma editável por humanos e
legível por agentes?

**Escolhido:** YAML (grounding-domains.yaml)

**Justificativa:**
- Kit já usa YAML para configuração (config.yml, shards/*.yaml)
- Legível sem treinamento (melhor que JSON para humanos)
- Suporta comentários — permite explicar cada fonte autoritativa
- PyYAML já é dependência do vitalia_context_engine.py

**Alternativas:**
- TOML: rejeitado — menos comum para listas de domínios, sem vantagem clara sobre YAML aqui
- JSON: rejeitado — sem suporte a comentários; dificulta edição humana
- Markdown: rejeitado — sem estrutura parseável para o context engine

---

## Decisão 2: Localização do grounding-domains.yaml Global

**Problema:** Onde colocar o arquivo global no kit?

**Escolhido:** `~/.vitalia/kit/config/grounding-domains.yaml`

**Justificativa:**
- Diretório `config/` ainda não existe — criação limpa, sem colisão
- Separação de concerns: `rules/` = comportamento do agente, `config/` = configuração de domínio
- Análogo ao padrão de outros ferramentas (ex: config/ em projetos Rails, Django)
- Não é symlink — é arquivo físico no kit, propagado para todos os projetos

**Alternativas:**
- `~/.vitalia/kit/rules/config/grounding-domains.yaml`: rejeitado — mistura regras com configuração
- `~/.vitalia/kit/extensions/grounding-domains.yaml`: rejeitado — extensions são workflows, não configuração
- Embedd no grounding.md: rejeitado — violaria SC-005 (≤ 60 linhas) e separação de concerns

---

## Decisão 3: Mecanismo de Override Local — JSONL + YAML Gerado

**Problema:** Como permitir que cada projeto customize domínios sem criar dependência de arquivo
manual sincronizado entre desenvolvedores?

**Escolhido:** `data/grounding-domains.jsonl` (append-only) → `consolidate()` → `grounding-domains-local.yaml`

**Justificativa:**
- Idêntico ao padrão já implementado: learnings.jsonl → LEARNINGS.md, decisions.jsonl → DECISIONS.md
- O JSONL é append-only: imutável, sem conflitos de merge entre máquinas
- `grounding-domains-local.yaml` é VIEW — gerado, nunca editado manualmente
- Distribuição automática via session-consolidate + git (já implementado)
- Audit trail completo pelo design (cada linha tem id, machine_id, timestamp)

**Alternativas:**
- Arquivo YAML editável manualmente por projeto: rejeitado — conflitos de merge, sem audit trail,
  sem propagação automática entre máquinas
- Patch/overlay sobre o global: rejeitado — complexidade desnecessária; JSONL + merge é mais simples

---

## Decisão 4: Tipo de Entrada scope_decision no JSONL

**Problema:** Como registrar a decisão de curação (global/local) sem violar a imutabilidade?

**Escolhido:** Entrada `scope_decision` como tipo separado no mesmo JSONL

**Justificativa:**
- Mantém o JSONL como única fonte de verdade para domínios locais
- A decisão é rastreável: quem decidiu, quando, em qual máquina
- O consolidate() resolve o escopo lendo pares (entrada original + scope_decision)
- Não introduz novo arquivo de infraestrutura

**Alternativas:**
- Editar o campo `scope` da entrada original: rejeitado — viola imutabilidade do JSONL
- Arquivo separado `scope-decisions.jsonl`: rejeitado — complexidade desnecessária; separa dados que
  pertencem ao mesmo registro lógico

---

## Decisão 5: Curadoria via ask_question (2 Rodadas)

**Problema:** Como apresentar a tabela de curadoria com seleção de destino (global/local/rejeitar)?

**Escolhido:** Tabela Markdown de contexto + ask_question multi-select em 2 rodadas

**Justificativa:**
- ask_question com is_multi_select: true é a ferramenta nativa do agente para seleção interativa
- 2 rodadas (A: global; B: local do restante) é mais claro que 3 opções por item (global/local/rejeitar)
  — evita ambiguidade quando o usuário quer rejeitar tudo que não foi para global
- A tabela markdown de contexto antecede as rodadas — o usuário lê antes de selecionar
- Implementação: zero código novo no context_engine.py — apenas instrução no .toml

**Alternativas:**
- 1 rodada com 3 opções por item: rejeitado — ask_question não suporta "by-row" selection;
  seria necessário 1 pergunta por domínio (verboso)
- CLI interativo no context_engine.py: rejeitado — o agente é o orquestrador; CLI seria
  duplicação de funcionalidade

---

## Decisão 6: Estrutura do Bloco grounding_rules nos Workflows

**Problema:** Como garantir que o agente execute o protocolo de grounding em cada workflow
sem depender apenas da regra always-on (que pode ser diluída pelo contexto)?

**Escolhido:** Bloco XML `<grounding_rules>` embutido no `prompt` de cada workflow crítico

**Justificativa:**
- O agente processa o conteúdo do prompt com mais atenção que regras globais quando há
  instrução explícita no próprio prompt
- XML tags são convenção da Anthropic para delimitação de seções de instrução
- Pode ser copiado de um .toml para o outro com pequenas adaptações (Fase 2 vs Fase 4)

**Alternativas:**
- Apenas grounding.md always-on: rejeitado — regra always-on pode ser "diluída" por contexto longo;
  bloco explícito no prompt é mais robusto
- Novo campo no .toml (ex: `grounding_preamble`): rejeitado — mudaria a estrutura do schema;
  embutir no `prompt` existente é compatível com versões anteriores

---

## Decisão 7: Modificação das Funções do vitalia_context_engine.py

**Problema:** Quais funções precisam ser modificadas e como evitar regressões?

**Escolhido:** Adicionar nova função `generate_grounding_yaml()` + modificar `consolidate_context()`,
`generate_dashboard()` e `init_context()`.

**Justificativa:**
- `generate_grounding_yaml()` isolada permite testar o merge logic separadamente
- `consolidate_context()` chama a nova função após as views existentes (mínimo de mudança)
- `generate_dashboard()` adiciona nova seção ao final (sem risco de quebrar seções existentes)
- `init_context()` adiciona criação do JSONL e yaml inicial (idêntico ao padrão dos outros JSONL)

**Riscos e mitigações:**
- Risco: grounding-domains.yaml global não encontrado → `generate_grounding_yaml()` loga warning
  e gera yaml local apenas com os itens do JSONL (fallback gracioso)
- Risco: JSONL malformado → parse individual por linha (try/except por linha, como learnings.jsonl)

---

## Rastro de Pesquisa — Este Documento

**Gerado em:** 12-08-2026 21:09(GMT-04:00)
**Domínios verificados:** python_packages (PyYAML), external_apis (N/A)

| # | Afirmação feita | Verificado? | Fonte consultada | Data |
|---|---|---|---|---|
| 1 | PyYAML já é dependência do vitalia_context_engine.py | Sim | grep "import yaml" no script — linha 9 | 12-08-2026 |
| 2 | Kit ainda não tem diretório config/ | Sim | ls ~/.vitalia/kit/config/ → "config/ inexistente" | 12-08-2026 |
| 3 | Extensions existentes: brainstorming, spec-specify, spec-plan, spec-tasks, spec-implement, session-end, session-consolidate | Sim | ls ~/.vitalia/kit/extensions/*.toml | 12-08-2026 |
