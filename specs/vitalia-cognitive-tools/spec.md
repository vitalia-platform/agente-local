<!-- vitalia-cognitive-tools.spec.md | Criado em: 24-07-2026 -->
# Especificação: Ferramentas Cognitivas e Autonomia do Agente

**Data:** 24-07-2026
**Autor/Agente:** Antigravity (Engenharia Reversa SDD)
**Status:** ⏳ AGUARDANDO APROVAÇÃO

---

## 1. Contexto e Objetivo (O Quê e Por Quê)
O orquestrador base possui ferramentas operacionais e ferramentas de I/O (RAG, Web Search). No entanto, para que o sistema de agentes (Arquiteto e Engenheiro) possua alta flexibilidade adaptativa e consiga superar alucinações (Agent Amnesia), eles necessitam de um "toolbelt cognitivo" interno.

O objetivo desta especificação é formalizar as três funções em `tools.py` que atuam sobre o próprio estado de memória do sistema: a recuperação do histórico de raciocínio da auditoria, a extração explícita de código da memória RAM e o carregamento dinâmico de habilidades (Skills).

---

## 2. Requisitos Funcionais e Não-Funcionais

### Requisitos Funcionais (FR-xxx)
- **FR-001**: O sistema **MUST** fornecer a ferramenta `read_working_memory(filepath)` que lê o estado de um arquivo salvo recentemente no Redis (`vitalia:hot_rag`).
- **FR-002**: O sistema **MUST** fornecer a ferramenta `query_audit_log(limit=5)` que executa um `XREVRANGE` na stream `vitalia:events` para retornar de forma legível os últimos turnos de raciocínio (Payload `reasoning`).
- **FR-003**: O sistema **MUST** fornecer a ferramenta `load_dynamic_skill(skill_name)` que lê o conteúdo bruto Markdown de `.specify/skills/<skill_name>/SKILL.md` para embuti-lo no prompt atual.

### Critérios de Sucesso (SC-xxx)
- **SC-001**: O `query_audit_log` **MUST** filtrar exclusivamente os eventos de `type: llm_turn` (ou raciocínios válidos identificáveis) para não inundar o limite de tokens do LLM com JSONs de telemetria indesejados.

---

## 3. User Stories & Acceptance Scenarios

### User Story 1 - [Extensibilidade via Skills Dinâmicas] (Priority: P1)
Como Agente Arquiteto, quero carregar regras de comportamento ou manuais técnicos (Skills) em tempo real, sem que precisem ser injetadas de antemão no meu System Prompt, economizando espaço.

**Why this priority**: Evita estourar os limites de contexto das LLMs injetando todo o conhecimento possível na largada (P1).

**Independent Test**: Solicitar que a ferramenta carregue um `SKILL.md` fictício e conferir o retorno da string.

**Acceptance Scenarios**:
1. **Given** que existe uma pasta `.specify/skills/ruby-expert/SKILL.md`
2. **When** o LLM chama `load_dynamic_skill("ruby-expert")`
3. **Then** a ferramenta lê o conteúdo Markdown via IO do disco
4. **Then** retorna a string completa como resultado da `FunctionCall` ao LLM.

### User Story 2 - [Recuperação de Contexto Quente] (Priority: P1)
Como Agente Engenheiro, quero extrair um script específico recém-gerado da memória (Redis) para usá-lo como base de uma edição.

**Why this priority**: Previne que o agente tente "adivinhar" o que ele gerou cinco turnos atrás, forçando um dogfooding (P1).

**Independent Test**: Salvar uma string mock no Redis na key `vitalia:hot_rag:teste.py` e chamar a ferramenta.

**Acceptance Scenarios**:
1. **Given** que o script `app.py` foi salvo há 10 minutos
2. **When** o Arquiteto pede uma refatoração e eu não tenho mais a classe em meu histórico local (head/tail)
3. **Then** chamo `read_working_memory("app.py")`
4. **Then** a string é devolvida do cache quente sem que precise acionar a lentidão do banco de dados vetorial frio (pgvector).

### User Story 3 - [Re-Auditoria de Raciocínio] (Priority: P2)
Como Arquiteto, quero investigar o que eu "pensei" no passado remoto da conversa lendo o log auditável do sistema, para resgatar decisões de planejamento descartadas da minha janela de tokens.

**Why this priority**: Fundamental para tarefas de longa duração que ultrapassam a limitação do context window (P2).

**Independent Test**: Mockar 10 eventos na Redis Stream `vitalia:events` e disparar a tool com limite de 5.

**Acceptance Scenarios**:
1. **Given** a stream `vitalia:events` preenchida com conversas, chamadas de tools e logs sistêmicos
2. **When** eu chamo `query_audit_log(3)`
3. **Then** a função executa a leitura bidirecional reversa, filtra apenas `llm_turn` (se houver), processa o parse do JSON e devolve as strings formatadas para minha leitura imediata.

---

## 4. Fora do Escopo
- Busca semântica nas habilidades (Skills). A chamada deve ocorrer estritamente pelo "nome do diretório" (`skill_name`) exato.
- Integração do Audit Log com o frontend (A leitura pelo dashboard é coberta pela `vitalia-dashboard.spec.md`).

---

## 5. Glossário
| Termo | Definição |
|---|---|
| **Hot Cache (Redis)** | Espaço alocado nas chaves `vitalia:hot_rag:*` onde scripts em edição são preservados para as sessões curtas |
| **Audit Log (Stream)** | O fluxo do barramento `vitalia:events` lido de forma retroativa (Reverse Range) pela ferramenta para recuperar memória fotográfica |
