# Tasks: Orquestrador AutoGen Vitalia

## Phase 1: Context Limiter
- [x] T001: Importar `HeadAndTailChatCompletionContext` no `main.py`.
- [x] T002: Injetar limitador nas configs do nó Engenheiro (Nó 2 - 6GB VRAM) durante a invocação do `ConversableAgent`.

## Phase 2: RAG Pipeline (AST)
- [x] T003: Desenvolver a função `chunk_code_ast` utilizando recursão na `tree = ast.parse(content)`.
- [x] T004: Adicionar persistência pgvector `INSERT INTO code_vectors` disparando requisições REST ao Ollama/nomic.

## Phase 3: Tool Binding & GroupChat
- [x] T005: Registrar as functions básicas (`web_search`, `update_sprint_state`) no Orquestrador.
- [x] T006: Iniciar o `RoundRobinGroupChat` controlando os turnos de fala.
