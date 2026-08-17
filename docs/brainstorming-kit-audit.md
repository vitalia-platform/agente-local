# 🧠 Brainstorming: Auditoria e Correção do Vitalia Kit
<!-- brainstorming-kit-audit.md | Atualizado em: 23-07-2026 09:29:00(GMT-04:00) -->

## Contexto

O usuário identificou que o Kit pode conter resquícios da arquitetura anterior (`~/.vitalia-spec`)
e bugs introduzidos durante a migração para v0.4.0. O objetivo é auditar e corrigir o kit
**antes** de qualquer trabalho no agente local.

---

## Achados da Auditoria (Read-Only)

### 🔴 BUG CRÍTICO 1 — Sed com sintaxe quebrada em `install-project.sh`

**Arquivo:** `~/.vitalia/kit/scripts/install-project.sh` (linhas 172–175)

```bash
# CÓDIGO ATUAL (QUEBRADO):
sed \
    -e "s|{{NAME}}/${ext_name}|g" \
    -e "s|{{DESCRIPTION}}/${desc}|g" \
    "${TEMPLATE}" > "${skill_file}"
```

**Problema:** A sintaxe do `sed` está completamente errada. O formato correto de substituição é `s|PATTERN|REPLACEMENT|flags`, mas o código usa `s|{{NAME}}/${ext_name}|g` — faltando o separador entre pattern e replacement. O `g` caiu no campo errado.

**Efeito:** Todo skill gerado via `install-project.sh` terá o template **não substituído** — os placeholders `{{NAME}}` e `{{DESCRIPTION}}` ficam literais nos arquivos `SKILL.md`. Isso explica por que o `brainstorming.toml` tem `description = "---"` (o placeholder foi copiado errado) e por que a versão do template no `SKILL.md` diz `Vitalia Kit 0.3` mesmo sendo v0.4.

**Correção necessária:**
```bash
sed \
    -e "s|{{NAME}}|${ext_name}|g" \
    -e "s|{{DESCRIPTION}}|${desc}|g" \
    "${TEMPLATE}" > "${skill_file}"
```

---

### 🔴 BUG CRÍTICO 2 — Paths de `.specify` hardcoded em múltiplos `.toml`

**Arquivos afetados:**
- `extensions/session-start.toml` (linhas 61, 67, 81, 86, 128, 156)
- `extensions/session-end.toml` (linhas 54, 75, 130, 134, 146, 149, 167, 179)
- `extensions/session-consolidate.toml` (linhas 68, 90, 105, 129, 147, 174, 193, 205)
- `rules/always-on/session-context.md` (linhas 3, 10, 13)

**Problema:** A v0.3 usava `.specify/memory/session/` como path de memória. A v0.4 migrou para `.vitalia/memory/session/`. Os templates `.toml` **nunca foram atualizados**. O agente que segue essas instruções vai buscar/gravar em paths que não existem.

**Situação do projeto local:** O projeto `test-agente-local` **já usa** `.vitalia/memory/session/` (correto para v0.4), mas o kit ainda instrui `.specify/`. Isso cria uma dissociação perigosa — o agente em outras máquinas pode criar o diretório errado.

**Correção necessária:** Substituir todas as ocorrências de `.specify/memory/session` por `.vitalia/memory/session` e `.specify/scripts` por uma referência ao kit global ou ao diretório correto do projeto.

---

### 🔴 BUG CRÍTICO 3 — Paths legados `~/.vitalia-spec` em `session-start.toml`

**Arquivo:** `extensions/session-start.toml` (linhas 75–76)

```
Ler: ~/.vitalia-spec/rules/always-on/architect-constitution.md
Ler: ~/.vitalia-spec/AGENTS.md
```

**Problema:** Instrução aponta para o path da versão anterior do kit (`~/.vitalia-spec/`). O caminho correto é `~/.vitalia/kit/rules/always-on/architect-constitution.yaml`. O agente que segue essa instrução vai falhar na leitura.

**Confirmado:** `~/.vitalia-spec` **não existe** no sistema atual.

---

### 🟡 PROBLEMA 4 — VERSION desatualizada no Kit

**Arquivo:** `~/.vitalia/kit/VERSION`  
**Conteúdo atual:** `0.3.0`  
**Conteúdo correto:** `0.4.0`

**Problema:** O kit foi refatorado para v0.4.0 (novo YAML da Constituição, nova estrutura de diretórios, Bandeira de Parada Técnica), mas o arquivo `VERSION` nunca foi atualizado. O script `bootstrap.sh` usa este arquivo para decidir se faz upgrade — com `0.3.0`, ele sempre vai tentar fazer upgrade ao invés de manter a versão atual.

---

### 🟡 PROBLEMA 5 — `bootstrap.sh` referencia versão `0.3.0` hardcoded

**Arquivo:** `~/.vitalia/kit/scripts/bootstrap.sh` (linha 16)

```bash
REQUIRED_VERSION="0.3.0"
```

Isso deve ser dinâmico ou atualizado junto com o `VERSION`.

---

### 🟡 PROBLEMA 6 — Template do SKILL.md menciona "Vitalia Kit 0.3"

**Arquivo:** `~/.vitalia/kit/integrations/antigravity/SKILL.md.template` (linha 6)

```
<!-- SKILL.md | Vitalia Kit 0.3 — gerado por install-project.sh -->
```

Deve referenciar a versão atual do kit dinamicamente (`{{KIT_VERSION}}`).

---

### 🟢 OBSERVAÇÃO 7 — `session-start.toml` instrui script inexistente

O `session-start.toml` instrui a executar:
```
$ python3 .specify/scripts/validate-kit.py --target .
$ bash .specify/scripts/session-resolve.sh
```

Esses scripts **não existem no kit atual** — nem no caminho `.specify/`, nem no caminho `.vitalia/`. A instrução de validação de ambiente está completamente morta. O agente que seguir isso vai falhar silenciosamente (como aconteceu ao iniciar esta sessão, onde o script não foi encontrado).

---

### 🟢 OBSERVAÇÃO 8 — `always-on/session-context.md` vs `architect-constitution.yaml`

O arquivo `session-context.md` existe em `rules/always-on/` mas referencia `.specify/` em vez de `.vitalia/`. Isso é inconsistente com a Constituição atualizada em YAML.

---

## Mapa de Correções Necessárias

| # | Severidade | Arquivo | Problema |
|---|---|---|---|
| 1 | 🔴 CRÍTICO | `scripts/install-project.sh` | Sintaxe `sed` quebrada — `{{NAME}}` e `{{DESCRIPTION}}` nunca substituídos |
| 2 | 🔴 CRÍTICO | `extensions/session-*.toml` | Paths `.specify/` hardcoded — deveriam ser `.vitalia/` |
| 3 | 🔴 CRÍTICO | `extensions/session-start.toml` | Path legado `~/.vitalia-spec/` — não existe mais |
| 4 | 🟡 ALTO | `VERSION` | Arquivo reporta `0.3.0`, kit é `0.4.0` |
| 5 | 🟡 ALTO | `scripts/bootstrap.sh` | `REQUIRED_VERSION` hardcoded em `0.3.0` |
| 6 | 🟡 MÉDIO | `integrations/antigravity/SKILL.md.template` | Menciona `Kit 0.3` no comentário HTML |
| 7 | 🟡 MÉDIO | `extensions/session-start.toml` | Instrui scripts (`validate-kit.py`, `session-resolve.sh`) que não existem |
| 8 | 🟢 BAIXO | `rules/always-on/session-context.md` | Paths `.specify/` hardcoded |

---

## Decisões para o Usuário

### Decisão A — Estratégia de substituição de paths

**Pergunta central:** Como resolver o hardcoding de `.specify/` nos `.toml`?

**Opção A1 — Substituição direta (simples, imediata)**
- Substituir todas as ocorrências de `.specify/memory/session` por `.vitalia/memory/session`
- Substituir `.specify/scripts` por scripts que existam no kit
- ✅ Simples de executar agora
- ❌ Se um projeto antigo ainda usa `.specify/`, vai quebrar

**Opção A2 — Variável `{{VITALIA_DIR}}` no template (solução arquitetural correta)**
- Introduzir um placeholder `{{VITALIA_DIR}}` nos `.toml` que é resolvido em tempo de instalação
- O `install-project.sh` escreve o valor real de `VITALIA_DIR` nos shims gerados
- ✅ Correto arquiteturalmente (agnóstico de path, conforme Artigo XXIII)
- ❌ Mais complexo — requer mudança na forma como os `.toml` são interpretados

**Opção A3 — Hybrid (substituição agora + variável para novas extensões)**
- Corrigir os `.toml` existentes agora com substituição direta
- Documentar `{{VITALIA_DIR}}` como padrão para futuras extensões
- ✅ Equilibrada: corrige o problema imediato sem bloquear o avanço

### Decisão B — Scripts inexistentes (`validate-kit.py`, `session-resolve.sh`)

**Pergunta:** O que fazer com as instruções que referenciam scripts ausentes?

**Opção B1 — Remover as instruções dos `.toml`**
- Simplificar o `session-start.toml` removendo as etapas que dependem de scripts não criados
- O agente simplesmente busca o `CONTEXT.md` diretamente

**Opção B2 — Criar os scripts mínimos agora**
- Criar `scripts/validate-kit.py` como um script simples que verifica a existência dos diretórios essenciais
- ✅ Completa a infraestrutura prometida pela v0.4.0

**Opção B3 — Substituir por instruções declarativas (sem scripts)**
- Converter a etapa de validação em uma checklist que o agente executa manualmente (lendo os arquivos e reportando)
- ✅ Sem dependências de scripts externos
- ✅ Mais resiliente (o agente consegue executar mesmo sem scripts)

### Decisão C — Ordem de trabalho

**Pergunta:** Corrigir o kit de forma atômica (todas as correções numa sessão) ou priorizar os críticos primeiro?

**Opção C1 — Tudo numa sessão**
- Resolve todos os 8 itens em sequência
- ✅ Consistência total ao final

**Opção C2 — Críticos primeiro (1, 2, 3), depois médios**
- Garante que o kit funciona minimamente antes de polir
- ✅ Menor risco de regressão
