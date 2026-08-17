<!-- spec.md | 12-08-2026 20:28(GMT-04:00) -->

# Especificação: Grounding Guard Rails v2

**Feature:** `006-grounding-guard-rails`
**Data:** 12-08-2026
**Autor/Agente:** Claude Sonnet 4.6 (Thinking) + André
**Preset:** software
**Status:** Rascunho — aguardando aprovação HITL

---

## 1. Contexto e Objetivo

### Problema

O pipeline SDD do Vitalia Kit (brainstorming → spec → plan → tasks → implement) não possui
nenhum mecanismo estrutural que impeça agentes LLM de usar conhecimento interno de treinamento
ao fazer afirmações sobre domínios externos (versões de bibliotecas, APIs, regulações, modelos
LLM, serviços em nuvem, etc.).

Isso resulta em afirmações incorretas ou desatualizadas que se propagam desde o brainstorming
até o código final, sem rastro verificável que permita ao humano auditar o processo.

### Evidência do Problema

Sessão de 30-07-2026: agente respondeu sobre capacidades do gemini usando
conhecimento de treinamento (sem busca). Na sessão de 12-08-2026, o próprio agente citou
lgpd.gov.br como URL oficial da LGPD — que não existe. URL correto: gov.br/anpd/pt-br.

### Objetivo

Implementar um sistema de Guard Rails de Grounding que:
1. Define os domínios onde verificação externa é obrigatória (YAML configurável)
2. Injeta o protocolo em todos os workflows do pipeline SDD
3. Gera um Rastro de Pesquisa auditável em cada artefato produzido
4. Permite que novos domínios sejam registrados via JSONL e curados no session-consolidate
5. Reflete o estado do sistema de grounding no DASHBOARD.md do contexto

---

## 2. Escopo

### Incluído

- Arquivo grounding-domains.yaml no kit global (editável por humanos)
- Arquivo grounding.md always-on (≤ 60 linhas)
- data/grounding-domains.jsonl append-only no repo de sessão
- grounding-domains-local.yaml gerado por consolidação
- Modificação de 6 workflows: brainstorming, spec-specify, spec-plan, spec-tasks, spec-implement, session-end
- Modificação do session-consolidate (Passo 3.5 — curadoria HITL)
- Modificação do vitalia_context_engine.py (funções consolidate, dashboard, init)
- Seção "Guard Rails de Grounding" no DASHBOARD.md

### Excluído

- Camada 3 Architectural (dynamic_retrieval_config, tool_config:ANY) — spec futura
- Skill vitalia-fact-check (Judge Pattern) — spec futura
- Skill vitalia-web-verify — spec futura
- Modificações na Constituição além de 1 linha de referência no Artigo XVIII

---

## 3. Requisitos Funcionais

### FR-001 — Arquivo de Domínios Global
**MUST** — O kit DEVE conter ~/.vitalia/kit/config/grounding-domains.yaml
com lista de domínios externos onde verificação obrigatória é exigida, fontes autoritativas
por domínio e lista de domínios isentos. O arquivo DEVE ser editável por humanos sem
conhecimento de código.

### FR-002 — Regra Always-On de Grounding
**MUST** — O kit DEVE conter ~/.vitalia/kit/rules/always-on/grounding.md com ≤ 60 linhas,
incluindo: protocolo de 4 passos (PARE/BUSQUE/CITE/SE SEM RESULTADO), lista resumida de
domínios verificáveis, template do Rastro de Pesquisa e bloco XML com comportamentos proibidos.

### FR-003 — JSONL de Domínios Locais (Append-Only)
**MUST** — O repo de sessão DEVE conter data/grounding-domains.jsonl com suporte a
4 tipos de entrada: new_domain, new_source, exempt e scope_decision. O arquivo
DEVE ser imutável (apenas append). Nenhum agente edita linhas existentes.

### FR-004 — Consolidação do YAML Local
**MUST** — O vitalia_context_engine.py DEVE gerar grounding-domains-local.yaml durante
--action consolidate, mergeando a base global com entradas do JSONL cujas scope_decision
sejam "local" ou "global". Entradas sem scope_decision (scope: null) NÃO aparecem
no yaml — ficam pendentes até curação.

### FR-005 — Rastro de Pesquisa nos Artefatos
**MUST** — Todo artefato gerado por workflow Vitalia (brainstorming, spec, plan, research.md)
que contenha afirmações sobre domínios verificáveis DEVE incluir seção padronizada de
Rastro de Pesquisa com tabela: afirmação / verificado? / fonte / data.

### FR-006 — Protocolo nos Workflows Críticos
**MUST** — Os workflows brainstorming.toml, spec-specify.toml, spec-plan.toml,
spec-tasks.toml e spec-implement.toml DEVEM conter bloco explícito de grounding_rules
e Passo 0 de identificação de domínios antes de qualquer execução.

### FR-007 — Phase 0 no spec-tasks
**MUST** — O spec-tasks.toml DEVE gerar automaticamente Phase 0 em todo tasks.md:
T000-A: Ativar venv
T000-B: Verificar versão Python do venv (não do sistema)
T000-C: Verificar deps instaladas vs requirements.txt
T000-D: Verificar versão atual de libs externas mencionadas na spec
T000-E: Rodar pip check para detectar conflitos

### FR-008 — Passo 0 no spec-implement
**MUST** — O spec-implement.toml DEVE expandir o Passo 4 (setup de ambiente) para incluir:
verificação do venv, versão Python do venv, pip check, e pesquisa de versão atual para
qualquer lib nova antes de adicionar ao requirements.

### FR-009 — Gate de Curadoria no session-consolidate
**MUST** — O session-consolidate.toml DEVE incluir Passo 3.5 que:
1. Detecta entradas scope:null no JSONL
2. Apresenta tabela de curadoria com ask_question em 2 rodadas (global / local)
3. Registra scope_decision no JSONL (append-only, com decided_by e timestamp)
4. Para decisões "global": apresenta diff e solicita confirmação HITL duplo antes de editar o kit

### FR-010 — Integração com DASHBOARD.md
**MUST** — O DASHBOARD.md DEVE incluir seção "Guard Rails de Grounding" com: status do
arquivo global, status/data do yaml local, contagem de entradas pendentes com alerta se > 0,
e link para o arquivo no GitHub.

### FR-011 — Init do JSONL
**SHOULD** — O vitalia_context_engine.py --action init DEVE criar data/grounding-domains.jsonl
vazio e grounding-domains-local.yaml inicial (cópia da base global), se não existirem.

### FR-012 — Session-End com Registro scope:null
**MUST** — O session-end.toml DEVE, após extração de aprendizados [KIT], verificar se
algum revela novo domínio de risco e, se aprovado pelo usuário, fazer append no JSONL com
scope:null (sem decidir global vs local — essa decisão fica para o session-consolidate).

---

## 4. Critérios de Sucesso

### SC-001 — Cobertura de Artefatos
Todo artefato produzido em brainstorming, spec-specify e spec-plan que mencione tecnologia
ou API externa contém seção "Rastro de Pesquisa" com pelo menos 1 entrada.

### SC-002 — Verificabilidade Humana
Para cada afirmação marcada como "Verificado: Sim", o humano pode abrir a URL e confirmar
a afirmação sem ambiguidade.

### SC-003 — Ciclo de Retroalimentação
Após 1 session-end com novo domínio aprovado + 1 session-consolidate, o domínio aparece
em grounding-domains-local.yaml com scope decidido pelo usuário.

### SC-004 — Visibilidade no Dashboard
O DASHBOARD.md exibe contagem correta de entradas pendentes. Quando há pendentes, exibe
"⚠️ N entradas aguardando curação". Quando nenhum, exibe "✅ 0 pendentes".

### SC-005 — Leveza do Always-On
O arquivo grounding.md tem ≤ 60 linhas após implementação.

### SC-006 — Constituição Preservada
Nenhum novo artigo na architect-constitution.md. Apenas 1 linha no Artigo XVIII.

### SC-007 — Compatibilidade de Ambiente
Toda spec com libs Python tem T000-E (pip check) concluído sem erros antes de implementação.

---

## 5. Histórias de Usuário

### US-1 — Domínios Configuráveis
Como desenvolvedor do kit Vitalia,
eu quero um arquivo YAML que liste os domínios onde verificação é obrigatória,
para que eu possa adicionar ou remover domínios sem alterar código dos workflows.

### US-2 — Rastro nos Artefatos
Como André revisando um artefato de brainstorming,
eu quero ver uma tabela de Rastro de Pesquisa ao final,
para que eu possa verificar cada afirmação factual de forma independente.

### US-3 — Phase 0 de Ambiente
Como agente executando spec-implement,
eu quero que o tasks.md tenha Phase 0 com verificação de ambiente,
para que eu nunca execute código em Python do sistema em vez do venv.

### US-4 — Curadoria de Domínios
Como André executando session-consolidate,
eu quero ver uma tabela de domínios recém-descobertos com opção de destiná-los
ao kit global ou manter locais.

### US-5 — Promoção para Global com HITL Duplo
Como André,
eu quero que a promoção de um domínio para o kit global exija confirmação explícita
após ver o diff do que será adicionado.

---

## 6. Cenários de Aceite

### AS-001 — Brainstorming com Domínio Verificável
Given que o grounding-domains.yaml contém o domínio python_packages
When o usuário executa brainstorming sobre feature que usa Django
Then o agente menciona verificação do domínio no Passo 0, cita fonte pypi.org
e inclui Rastro de Pesquisa ao final com linha para Django

### AS-002 — Rastro com Item Não Verificado
Given que um artefato foi gerado com afirmação não verificada
When o usuário lê o Rastro de Pesquisa
Then a linha correspondente contém "NAO VERIFICADO" e status ⚠️

### AS-003 — Phase 0 Gerada Automaticamente
Given que spec-tasks.toml foi modificado
When o usuário executa /vitalia-spec-tasks para qualquer feature
Then o tasks.md contém Phase 0 com T000-A como primeiro item (ativar venv)
e T000-B como segundo (verificar Python do venv)

### AS-004 — Curadoria HITL no Consolidate
Given que há 2 entradas no grounding-domains.jsonl com scope:null
When o usuário executa /vitalia-session-consolidate
Then o agente apresenta tabela e ask_question em 2 rodadas, registra 2 scope_decision
no JSONL e o yaml é regenerado corretamente

### AS-005 — Dashboard com Pendentes
Given que há entradas sem scope_decision no JSONL
When o context engine gera o DASHBOARD.md
Then a seção Guard Rails exibe "⚠️ N entradas aguardando curação"

### AS-006 — Dashboard Limpo
Given que todas as entradas têm scope_decision
When o context engine gera o DASHBOARD.md
Then a seção Guard Rails exibe "✅ 0 pendentes"

---

## 7. Fora do Escopo

- Camada Arquitetural de API (dynamic_retrieval_config, tool_config:ANY)
- Skill vitalia-fact-check (Judge Pattern pós-output)
- Suporte a linguagens além de Python no T000-x (Node.js, etc.) — versão futura
- Interface web/GUI para curadoria

---

## 8. Dependências e Suposições

- Dependência: vitalia_context_engine.py é o único gerador do DASHBOARD.md e arquivos de sessão
- Dependência: O sistema já suporta arquivos JSONL append-only (learnings, decisions)
- Suposição: O agente (Antigravity) tem acesso ao ask_question multi-select nativo
- Suposição: O kit global está em ~/.vitalia/kit/ e os symlinks do projeto apontam para ele

---

## Rastro de Pesquisa — Esta Spec

**Gerado em:** 12-08-2026 20:28(GMT-04:00)
**Domínios verificados:** N/A

Toda a informação técnica nesta spec é derivada do BRAINSTORMING_GROUNDING_V2_PLAN.md
cujas afirmações externas já possuem rastro verificado.
