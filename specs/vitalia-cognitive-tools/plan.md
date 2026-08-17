# Implementation Plan: Ferramentas Cognitivas e Autonomia do Agente

**Date**: 24-07-2026 | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/agente-local-v2/specs/vitalia-cognitive-tools/spec.md)

## Summary
Adição das ferramentas `query_audit_log`, `read_working_memory` e `load_dynamic_skill` ao sistema de I/O do Orquestrador, permitindo autoconsciência de sessão e resgate imediato de memória.

## Technical Context
**Language/Version**: Python 3.11+
**Storage**: Redis (`vitalia:events` para auditoria, `vitalia:hot_rag:*` para memória)
**Project Type**: Agentic Tools Extension

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| P05: Extensibilidade | ✅ PASS | `load_dynamic_skill` permite anexar regras s/ alterar core. |

## Technical Decisions

1. **Redis XREVRANGE vs SQL**: Decidimos usar a Stream do Redis para a auditoria fotográfica do LLM pois os logs de raciocínio são episódicos e expiram após a sessão. O uso de bancos relacionais seria excessivamente lento.
2. **Dynamic Skill Parsing**: Lemos direto do disco (`.specify/skills/`) pois é o formato padrão do Antigravity (Markdown com frontmatter) — a ferramenta repassa tudo como uma única string injetada no prompt dinâmico.

## Phase Overview
### Phase 1: Ferramenta de Audit
### Phase 2: Memória de Curto Prazo (Hot Cache)
### Phase 3: Sistema Dinâmico de Skills
