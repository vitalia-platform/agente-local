<!-- vitalia-orchestrator.spec.md | Atualizado em: 24-06-2026 21:18:00(GMT-04:00) -->

# Especificação de Funcionalidade: Orquestrador AutoGen Vitalia (Topologia Cross-WSL e Redis State)

**Data:** 24-06-2026
**Autor/Agente:** Antigravity (Arquiteto)

## 1. Contexto e Objetivo (O Quê e Por Quê)
O projeto "agente-local" visa construir o cérebro (Orquestrador) do Vitalia Kit utilizando AutoGen 0.5.x. O hardware disponível impõe um gargalo severo (Nó 2 possui uma GTX 1060 de 6GB de VRAM), o que inviabiliza carregar múltiplos agentes massivos simultaneamente sem incorrer em swap (OOM). Adicionalmente, o uso de repositórios Git locais para troca de estado entre agentes provou-se ineficiente e propenso a falhas de lock. O objetivo desta spec é padronizar a separação cognitiva: O Arquiteto rodará na RAM/CPU local do Nó 1, e o Engenheiro tomará 100% da VRAM do Nó 2, com o estado do sistema intermediado via cache em memória (Redis híbrido AOF/RDB). O sistema contará também com RAG otimizado por sintaxe (AST chunking), recursos de busca na web, e um sistema de Pub/Sub opcional para troca de contexto.

## 2. Requisitos Funcionais
O que o software deve fazer de forma observável?
- [ ] O orquestrador (`vitalia-core/main.py`) deve inicializar um `RoundRobinGroupChat` com 1 Arquiteto e 1 Engenheiro via nova API (`autogen-agentchat`).
- [ ] O Arquiteto deve fazer chamadas de inferência exclusivamente para a API do Ollama no Nó 1.
- [ ] O Engenheiro deve fazer chamadas de inferência exclusivamente para a API do Ollama no Nó 2.
- [ ] O sistema deve implementar uma Tool `save_code_to_rag(filepath, content)` com **Estratégia Hot/Cold**: salva temporariamente no Redis (Hot) e permanentemente no PostgreSQL (`pgvector`) (Cold). O chunking (AST Chunking) deve processar e isolar blocos de código (preservando funções/classes inteiras).
- [ ] O sistema deve implementar **Context Injection**: extrair contexto relevante do RAG/Redis e injetar diretamente no *Tail* do histórico do Engenheiro antes do seu turno.
- [ ] O sistema deve implementar uma Tool `web_search(query)` permitindo pesquisar informações atualizadas na internet.
- [ ] O sistema deve implementar uma Tool `update_sprint_state(task, status)` que persiste o andamento das missões no Redis.
- [ ] A API de telemetria (`telemetry_api.py`) deve retornar uso bruto de memória via `nvidia-smi` em formato JSON.

## 3. Requisitos Não-Funcionais (Restrições)
Quais as regras de performance, segurança, ou aderência à Constituição do Arquiteto?
- [ ] **Constituição - Artigo I e III (Test-First):** Todo arquivo em `vitalia-core` deve possuir testes unitários e **Testes End-to-End (E2E)** simulando o fluxo.
- [ ] **Constituição - Artigo VI e XII (Zero Hardcoding):** As URLs base não devem estar completas no `.env` (ex: `NO2_SERVER_IP=192.168.0.220`, `DB_HOST=localhost`). O código deve montar a URL final.
- [ ] **Constituição - Artigo XIV (Simplicidade / Desacoplamento Limpo):** O código Python residirá estritamente no diretório `vitalia-core/`. Para não quebrar a convenção do ecossistema e ferramentas padrão, a infraestrutura base (`.env`, `docker-compose.yml`) residirá na **raiz do projeto**. Conexões DB usarão `psycopg2.pool.SimpleConnectionPool` (YAGNI).
- [ ] **Proteção de VRAM Crítica (Head & Tail):** O Agente Engenheiro deve usar `HeadAndTailChatCompletionContext` (Head=1, Tail=M) com um limite estrito de **7000 tokens** medidos via `tiktoken` para proteger os 6GB da GTX 1060, preservando o `system_message` e definições de tools no Head.
- [ ] **Persistência Redis:** O Redis deve ser configurado no modo híbrido AOF+RDB (`appendfsync everysec`, `aof-use-rdb-preamble yes`) no compose para garantir resiliência do estado da sprint.
- [ ] **Pub/Sub (Feature Flags):** Implementar flags de granularidade fina no `.env` (`VITALIA_PUBSUB_ENABLED`, `VITALIA_PUBSUB_ARCHITECT_PUBLISH`, `VITALIA_PUBSUB_ENGINEER_SUBSCRIBE`, `VITALIA_PUBSUB_CHANNEL`).

## 4. Histórias de Usuário (User Stories)
**Como um** [Engenheiro do AutoGen], **eu quero** [ter monopólio da VRAM no Nó 2 com contexto protegido por Head&Tail] **para que** [minhas regras base nunca sejam esquecidas e eu não cause OOM].
**Como um** [Arquiteto do AutoGen], **eu quero** [que o RAG use uma estratégia Hot/Cold e Injeção de Contexto] **para que** [o código da sessão atual seja acessado instantaneamente e injetado no meu contexto, e o código legado seja preservado].
**Como** [Sistema Orquestrador], **eu quero** [controlar a comunicação assíncrona entre agentes via Pub/Sub do Redis] **para que** [eu possa ativar ou desativar canais de insight via flags de ambiente].

## 5. Critérios de Aceite (Acceptance Criteria)
Condições estritas para considerar a funcionalidade concluída.
- [ ] Testes unitários e E2E passando (`pytest vitalia-core/tests`).
- [ ] O AST Chunking processa um arquivo Python sem fragmentar funções/classes.
- [ ] IPs do banco, Redis e Ollama são lidos do `.env` e as URLs montadas dinamicamente.
- [ ] O `docker-compose.yml` inclui as flags AOF/RDB para o serviço Redis.
- [ ] As ferramentas base estão funcionais e o pool de conexão do PostgreSQL (`SimpleConnectionPool`) está implementado.
- [ ] O Engenheiro está configurado com `HeadAndTailChatCompletionContext`.

## 6. Fora do Escopo (Out of Scope)
O que NÃO será feito nesta etapa (para evitar scope creep).
- [ ] Configuração interna de provisionamento das imagens do Ollama nos clusters.
- [ ] Interface visual ou painéis gráficos adicionais além da Open WebUI.
- [ ] Migração completa para SQLAlchemy (mantido `psycopg2` via pool simples).
