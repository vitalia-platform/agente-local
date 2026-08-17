<!-- vitalia-orchestrator.spec.md | Atualizado em: 24-07-2026 -->
# Especificação: Orquestrador AutoGen Vitalia (Topologia Cross-WSL e Redis State)

**Data:** 24-06-2026 (Refatorado em 24-07-2026 para SDD v0.4.0 As-Built)
**Autor/Agente:** Antigravity
**Status:** ⏳ AGUARDANDO APROVAÇÃO

---

## 1. Contexto e Objetivo (O Quê e Por Quê)
O projeto constrói o cérebro (Orquestrador) do Vitalia Kit utilizando AutoGen (pacotes `autogen-agentchat` e `autogen-core`). Devido ao gargalo de hardware, o sistema divide a inferência entre nós usando perfis Ollama dinâmicos lidos do `.env`. Para contornar a limitação de VRAM e o problema de loops OOM, o estado da conversação é filtrado via `HeadAndTailChatCompletionContext`, e o compartilhamento de arquivos ocorre via uma estratégia de RAG (Retrieval-Augmented Generation) "Hot/Cold" intermediada por Redis e PostgreSQL (`pgvector`).

---

## 2. Requisitos Funcionais e Não-Funcionais

### Requisitos Funcionais (FR-xxx)
- **FR-001**: O orquestrador (`main.py`) **MUST** construir um `RoundRobinGroupChat` com 1 Arquiteto e 1 Engenheiro.
- **FR-002**: O sistema **MUST** proteger a memória (VRAM) aplicando o limitador `HeadAndTailChatCompletionContext(head_size=1, tail_size=20)` ao Engenheiro.
- **FR-003**: O sistema **MUST** implementar uma ferramenta `save_code_to_rag` que quebra arquivos de código isolando funções/classes usando o módulo nativo `ast` (AST Chunking).
- **FR-004**: O sistema **MUST** implementar a ferramenta `web_search` utilizando a biblioteca `duckduckgo-search` (DDGS), retornando os 3 melhores links e resumos.
- **FR-005**: O sistema **MUST** sincronizar o progresso no Redis via `update_sprint_state(task, status)`.

### Critérios de Sucesso (SC-xxx)
- **SC-001**: O AST Chunking deve garantir que nenhuma função (node `ast.FunctionDef`) ou classe (node `ast.ClassDef`) sofra quebra no meio da sua lógica durante o split.
- **SC-002**: Se as chamadas para as ferramentas quebrarem, o erro (`Exception`) deve ser convertido em uma string limpa e enviada de volta para que o LLM entenda o que falhou sem ocasionar um `sys.exit(1)`.

---

## 3. User Stories & Acceptance Scenarios

### User Story 1 - [Proteção de Memória Head/Tail] (Priority: P1)
Como um Engenheiro do AutoGen rodando em uma GTX 1060 (6GB), quero que meu contexto preserve estritamente o System Prompt inicial e apague apenas as mensagens do meio, para que eu nunca esqueça das minhas instruções vitais de uso de RAG.

**Why this priority**: Evitar alucinações ("Agent Amnesia") e travamentos por Out of Memory (OOM) (P1).

**Independent Test**: Simular 30 turnos de conversa e verificar o payload final passado ao LLM; deve conter a instrução system e apenas as 20 últimas mensagens do tail.

**Acceptance Scenarios**:
1. **Given** que o GroupChat chegou a 25 mensagens
2. **When** for a vez do Engenheiro processar a inferência
3. **Then** o `HeadAndTailChatCompletionContext` irá descartar as mensagens 2 a 5
4. **Then** a resposta ocorrerá dentro do limite da janela do modelo sem falha.

### User Story 2 - [RAG: AST Chunking Hot/Cold] (Priority: P1)
Como Arquiteto, quero salvar o código gerado pelo Engenheiro no RAG para recuperação futura. O código não deve ser cortado de forma arbitrária (ex: a cada 500 caracteres), mas sim por escopos lógicos (classes/funções).

**Why this priority**: Chunks estúpidos quebram a semântica de métodos durante o retrieval.

**Independent Test**: Passar um script Python com 3 funções grandes pelo `chunk_code_ast` e checar o tamanho do array resultante.

**Acceptance Scenarios**:
1. **Given** um arquivo contendo a classe `User` e a função `calculate()`
2. **When** o agente chama `save_code_to_rag(filepath, content)`
3. **Then** o sistema gera um chunk limpo para a classe e outro para a função
4. **Then** o sistema salva temporariamente no Redis (`vitalia:hot_rag`)
5. **Then** gera os embeddings e persiste no PostgreSQL (`code_vectors`).

---

## 4. Fora do Escopo
- Provisionamento das imagens Ollama nos nós.
- Adição de novos perfis de agentes especialistas (mantém-se Arquiteto e Engenheiro).

---

## 5. Glossário
| Termo | Definição |
|---|---|
| **Hot Cache** | Armazenamento temporário volátil de rápido acesso (Redis), expirando em 24h |
| **Cold Storage** | Armazenamento analítico e permanente (PostgreSQL + pgvector) para busca semântica futura |
| **AST Chunking** | Parsing estruturado do Python via Abstract Syntax Tree (`ast.parse`) em vez de divisão baseada no tamanho por caracteres |
