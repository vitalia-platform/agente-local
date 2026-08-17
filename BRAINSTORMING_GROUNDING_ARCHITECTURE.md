<!-- BRAINSTORMING_GROUNDING_ARCHITECTURE.md | 12-08-2026 21:46(GMT-04:00) -->

# Brainstorming: Prevenção de Uso de Conhecimento Interno em Workflows Agenticos

> Sessão: 30-07-2026 | Modelo: Claude Sonnet 4.6 + André  
> Baseado em buscas: ai.google.dev, Gemini API docs, pesquisa de 2026 sobre agentic grounding  
> Status: **✅ Guard Rails v2 IMPLEMENTADO — 12-08-2026** | Camada 3 (Architectural): spec futura

---

## Contexto

Durante a sessão de brainstorming sobre modelos LLM, o agente (Claude Sonnet 4.6) respondeu sobre capacidades do `gemini-3.1-pro-preview` usando **conhecimento interno de treinamento** sem buscar fontes oficiais. A avaliação estava incorreta. O usuário detectou e solicitou busca web, que revelou o modelo como um Pro tier de alto desempenho — invertendo a recomendação original.

**Comportamento paralelo identificado:** modelos executam comandos Python fora do ambiente virtual, consumindo tokens desnecessários e potencialmente usando versões erradas de dependências.

---

## O Problema Raiz (Verificado em Pesquisa)

A pesquisa de 2026 confirma: **prompts texto são camadas "soft" — probabilísticas, não determinísticas.**

> "LLMs são incentivados a 'blefar' devido aos objetivos de predição do próximo token, que recompensam respostas confiantes em vez de incerteza calibrada."

Um LLM que recebe "pesquise na web antes de responder" trata isso como sugestão competindo com seu treinamento. "Always search" perde para "answer directly" se o modelo foi treinado a ser confiante.

---

## Camadas de Defesa Mapeadas

### Camada 1 — Prompt Guard Rails (Soft Layer)

**1A: Decision Framework Explícito**
```toml
## Regras de Grounding (OBRIGATÓRIO)
ANTES de afirmações sobre: versões de modelos LLM, capacidades de APIs, 
benchmarks, preços, lançamentos pós-2024:
→ DEVE chamar search_web nos sites oficiais
→ NUNCA use conhecimento interno para estes domínios
→ Se sem resultado: declare "não encontrei fonte"
```

**1B: Citation Contract Persona**
Coupling de persona "Strict Citation Contract" — toda afirmação sobre sistemas externos cita a fonte consultada na sessão.

**1C: Negative Constraints com delimitadores XML**
```xml
<tool_rules>
PROIBIDO responder sobre versões de modelos sem search_web.
PROIBIDO marcar tasks [x] sem executar o comando correspondente.
PROIBIDO executar python/pip fora do ambiente virtual ativo.
</tool_rules>
```

### Camada 2 — Estrutura de Workflow (Hard Layer no Kit)

**2A: Passo 0 Obrigatório em spec-implement**
Sub-task de verificação de ambiente antes de qualquer execução:
- Localizar ambiente virtual (find .venv, venv, env)
- Ativar e verificar versões
- Confirmar dependências presentes

**2B: Skill `vitalia-web-verify`** *(nova skill — spec futura)*
```
/vitalia-web-verify model gemini-3.1-pro-preview
/vitalia-web-verify api PyYAML version
```

**2C: Sub-tasks de pesquisa explícitas no tasks.md**
Tasks T000-x como pré-requisitos do Phase 1, forçando verificação de ambiente e dependências antes de qualquer execução.

### Camada 3 — Controle de API (Architectural Hard Layer — ESCOPO FUTURO)

**3A: dynamic_retrieval_config com threshold baixo**
```python
tools = {
    "google_search_retrieval": {
        "dynamic_retrieval_config": {
            "dynamic_threshold": 0.06  # força busca em quase toda query factual
        }
    }
}
```
Default do Gemini é 0.3 — reduzir para 0.06 força grounding em mais queries.

**3B: tool_config: mode="ANY" para tasks de verificação**
```python
tool_config = types.ToolConfig(
    function_calling_config=types.FunctionCallingConfig(mode="ANY")
)
```
Força function calling para tasks onde o kit exige verificação externa.

**Implementação no Kit:** Requer que agente-local exponha controles de API como hooks configuráveis nos `.toml`:
```toml
[tools]
grounding_threshold = 0.06      # injeta dynamic_retrieval_config
force_tool_use = ["T000-A", "T000-B"]  # injeta tool_config:ANY para tasks específicas
```

### Camada 4 — Judge Pattern (Pós-Validação)

Skill `vitalia-fact-check` (spec futura): após qualquer output com afirmações sobre sistemas externos, o agente auto-avalia "Verifiquei com busca? Sim/Não". Se Não: executa busca e corrige antes de finalizar.

---

## Matriz de Decisão

| Camada | Esforço | Confiabilidade | Status |
|---|---|---|---|
| 1A — Decision Framework no prompt | Baixo | Média | ✅ Aplicado — `<grounding_rules>` em 5 workflows |
| 1B — Citation Contract | Baixo | Média-Alta | ✅ Aplicado — Rastro de Pesquisa obrigatório nos artefatos |
| 1C — Negative Constraints XML | Baixo | Média | ✅ Aplicado — bloco `<grounding_rules>` XML em todos os workflows |
| 2A — Passo 0 no spec-implement | Médio | Alta | ✅ Aplicado — Passo 4 expandido (venv + pip check + compat) |
| 2B — Skill vitalia-web-verify | Médio | Alta | 🔵 Spec futura |
| 2C — Sub-tasks de pesquisa no tasks.md | Baixo | Alta | ✅ Aplicado — Phase 0 (T000-A..T000-E) gerada automaticamente |
| 2D — grounding-domains.yaml configurável | Baixo | Alta | ✅ **[NOVO v2]** — 7 domínios + fontes verificadas + isenções |
| 2E — grounding.md always-on (≤ 60 linhas) | Baixo | Alta | ✅ **[NOVO v2]** — 54 linhas, ativa em toda sessão |
| 2F — JSONL append-only + curadoria HITL | Médio | Alta | ✅ **[NOVO v2]** — session-end + session-consolidate Passo 3.5 |
| 2G — Dashboard Guard Rails | Baixo | Média | ✅ **[NOVO v2]** — seção Guard Rails no DASHBOARD.md |
| 3A — dynamic_retrieval_config | Alto | Muito Alta | 🔵 Spec futura (Architectural) |
| 3B — tool_config: ANY | Alto | Muito Alta | 🔵 Spec futura (Architectural) |
| 4 — Judge / fact-check | Médio | Alta | 🔵 Spec futura |

---

## Decisão Tomada

- **Para spec-implement SPEC-004 (agora):** Camada 1 (guard rails) + 2C (sub-tasks T000-x)
- **Estratégia de longo prazo:** Architectural Hard Layer (Camada 3) via spec dedicada
- **Próximo item para spec:** Expor `grounding_threshold` e `force_tool_use` como parâmetros configuráveis nos `.toml` do kit, para que o agente-local os injete no `GenerateContentConfig` da Gemini API

---

## Comportamentos a Prevenir (Checklist para Guard Rails)

1. ❌ Usar conhecimento interno sobre versões/capacidades de modelos LLM
2. ❌ Usar conhecimento interno sobre versões de bibliotecas/APIs externas
3. ❌ Executar `python` ou `pip` fora do ambiente virtual ativo
4. ❌ Marcar tasks `[x]` sem executar o comando correspondente
5. ❌ Afirmar capacidades de modelos sem citar fonte verificada nesta sessão

