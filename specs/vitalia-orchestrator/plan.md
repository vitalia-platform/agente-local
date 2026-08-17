# Implementation Plan: Orquestrador AutoGen Vitalia

**Date**: 24-07-2026 | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/agente-local-v2/specs/vitalia-orchestrator/spec.md)

## Summary
Estruturação do `main.py` com `autogen` limitando o contexto da VRAM e aplicando estratégia híbrida de busca RAG (AST-based).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `autogen-agentchat`, `autogen-core`, `psycopg2`, `pgvector`
**Storage**: PostgreSQL (`code_vectors`)
**Target Platform**: Servidor Node 1 (Local) e Node 2 (Remoto)
**Project Type**: Agentic Orchestrator

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| P02: Confiabilidade LLM | ✅ PASS | Proteção contra OOM com limitador rígido `HeadAndTailChatCompletionContext` implementada |

## Technical Decisions

1. **Limitador de Contexto AutoGen**: Usaremos `HeadAndTailChatCompletionContext(head_size=1, tail_size=20)`. Preserva o system prompt e deleta o meio para proteger placas como a GTX 1060 (6GB).
2. **Chunking AST vs Raw**: Text Splitters de LangChain frequentemente quebram código Python no meio da definição de funções. Optamos por usar o módulo `ast` padrão do Python. A iteração ocorre em `ast.FunctionDef` e `ast.ClassDef`, garantindo precisão semântica na quebra de chunks do RAG.
3. **Embeddings Model**: Fixado em `nomic-embed-text` servido localmente via Ollama para evitar chamadas lentas à OpenAI.

## Phase Overview

### Phase 1: Context Limiter
### Phase 2: RAG Pipeline (AST)
### Phase 3: Tool Binding & GroupChat
