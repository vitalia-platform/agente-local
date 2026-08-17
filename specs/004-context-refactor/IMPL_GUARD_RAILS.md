<!-- IMPL_GUARD_RAILS.md | SPEC-004 | 30-07-2026 -->
<!-- Leia este arquivo ANTES de iniciar /vitalia-spec-implement -->

# Guard Rails — Implementação SPEC-004

> **Para o agente que executará o /vitalia-spec-implement:**  
> Este arquivo contém regras de comportamento obrigatórias.  
> Não são sugestões. São gates. Violar qualquer regra = PARAR e reportar.

---

## REGRA 1 — Ambiente Virtual (Bloqueante)

**NUNCA** execute `python`, `python3` ou `pip` diretamente no shell sem antes:
1. Ter completado a Phase 0 do `tasks.md` (T000-A a T000-F)
2. Ter o venv ativado e confirmado

```bash
# Forma ERRADA (proibida):
python3 vitalia_context_engine.py --action init
pip install pyyaml

# Forma CORRETA:
# 1. Encontrar: find . -name "activate" -path "*/bin/activate"
# 2. Ativar: source .venv/bin/activate (ou equivalente encontrado)
# 3. Confirmar: which python3  # deve apontar para o venv
# 4. Então executar o comando
```

Se não houver venv: **PARAR**. Reportar ao usuário. Aguardar instrução.

---

## REGRA 2 — Conhecimento Interno Proibido

Para qualquer afirmação sobre os domínios abaixo, **DEVE** executar `search_web` em sites oficiais antes de responder:

| Domínio | Sites oficiais a consultar |
|---|---|
| Modelos LLM (versões, capacidades, benchmarks) | ai.google.dev, anthropic.com, openai.com |
| PyYAML, hashlib, stdlib Python | docs.python.org, pypi.org |
| Gemini API, tool_config, grounding | ai.google.dev/gemini-api/docs |
| Git comportamento | git-scm.com |

Se `search_web` não retornar resultado relevante: declare **"não encontrei fonte — aguardando input do usuário"**. Nunca invente.

---

## REGRA 3 — Tasks São Gates Físicos

- `[ ]` = não iniciada
- `[/]` = em execução (opcional — marque ao iniciar)
- `[x]` = **concluída E validada**

**Proibido** marcar `[x]` sem:
1. Ter executado o comando exato da task
2. Ter verificado que o output foi o esperado (exit code 0 ou output específico)

---

## REGRA 4 — Citation Contract

Ao fazer qualquer afirmação sobre sistemas externos nesta sessão:

```
✅ CORRETO: "PyYAML 6.0.1 está instalado [Fonte: run_command pip show pyyaml]"
❌ ERRADO:  "PyYAML deve estar instalado pois é dependência comum"
```

---

## REGRA 5 — Erros São Bloqueantes

Se qualquer `run_command` retornar exit code != 0:
1. **PARAR** — não prosseguir para a próxima task
2. Exibir o erro completo ao usuário
3. Aguardar instrução explícita

Não tente "contornar" erros silenciosamente.

---

## Checklist de Início de Sessão

Antes de iniciar qualquer task, confirme:

- [ ] Li o `tasks.md` completo (incluindo o bloco de guard rails)
- [ ] Completei Phase 0 (T000-A a T000-F) com sucesso
- [ ] Venv está ativo e `which python3` aponta para ele
- [ ] PyYAML está disponível no venv
- [ ] Git e sub-repo de contexto estão configurados

Só então iniciar Phase 1.

---

## Sobre Conhecimento de Modelos LLM

Este projeto foi desenvolvido em sessão com **Claude Sonnet 4.6**.  
O `/vitalia-spec-implement` será executado por **gemini-3.1-pro-preview**.

Características verificadas via busca oficial (ai.google.dev, 30-07-2026):
- Contexto: 1M tokens input / 65k output
- Otimizado para agentic workflows e bash execution
- Thinking tiers: Low / Medium / High
- Endpoint especializado: `gemini-3.1-pro-preview-customtools`

**Não use conhecimento interno para complementar ou atualizar estas informações.**  
Se precisar de mais detalhes: busque em ai.google.dev.
