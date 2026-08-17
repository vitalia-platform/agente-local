# Specification: Observability Enhancement & Tool Diagnostics

**Status**: DRAFT
**Context**: O backend atual (vitalia-core) possui um `logger.py` unificado via Redis Streams e Shards, mas as ferramentas isoladas (como `save_code_to_rag`) falham silenciosamente ou apenas retornam strings de erro. O fluxo do orquestrador não detalha para qual nó (Nó 1 ou Nó 2) a requisição está sendo enviada, nem captura vazamentos de JSON de modelos sem suporte total a Tool Calling Nativo (como Qwen2.5).

## 1. Problem Statement
Sem uma malha de observabilidade densa, o desenvolvimento e depuração de ferramentas e modelos distribuídos se torna impraticável. Quando uma ferramenta falha, a causa (falta de Redis, tabela PostgreSQL faltando, timeout do Ollama) fica invisível para o desenvolvedor. Além disso, a configuração do modelo do servidor precisa ser ajustada para usar o Tool Bridge customizado ao invés da chamada nativa da API.

## 2. Functional Requirements (FR)
- **FR-001 (MUST)**: O arquivo `.env` deve ser atualizado para configurar `NO2_TOOL_CALLING_NATIVE=false`, permitindo que o `VitaliaOllamaClient` intercepte as intenções de ferramentas de modelos menos capazes.
- **FR-002 (MUST)**: O módulo `tools.py` deve incorporar a instância global do `logger`. Toda ferramenta crítica (ex: `save_code_to_rag`) deve emitir eventos `system_log` documentando o início de execução, falhas em dependências externas (Redis, DB, Ollama Embeddings) e o sucesso final.
- **FR-003 (MUST)**: O orquestrador (`main.py`) deve imprimir no console e emitir no logger a URL exata do nó (Nó 1 ou Nó 2) selecionada para o turno, garantindo transparência de roteamento.
- **FR-004 (SHOULD)**: A ferramenta `save_code_to_rag` deve possuir testes formais (TDD) em `vitalia-core/tests/` utilizando o **banco de dados PostgreSQL local real** (E2E), com provisão de comandos para sanitização final.
- **FR-005 (MUST)**: O `logger.py` deve atuar como o **Único Canal de Comunicação Executivo (Single Source of Truth)**. Sempre que qualquer componente (código, LLMs, Humanos) precisar saber sobre o fluxo de execuções, deverá obrigatoriamente ler e escrever dados nesta fila. Quando o Redis estiver inativo, ele deve realizar fallback para gravação em arquivos no diretório `data_storage` (conforme config do kit) ou em uma pasta `/logs` na raiz (com a respectiva adição ao `.gitignore`).
- **FR-006 (MUST)**: Deve existir um mecanismo unificado para que ferramentas ou LLMs sinalizem impossibilidades técnicas (ex: banco indisponível, modelo alucinando formato). Esse sinal de impossibilidade deve **obrigatoriamente** desencadear o encerramento do processo (`__VITALIA_ABORT__`) para prevenir loops infinitos e colisões com linguagem natural.
- **FR-007 (MUST)**: Sigilo e Criptografia do Canal. O conteúdo sensível trafegado na fila executiva ou salvo em logs de fallback deve ser protegido por criptografia de ponta a ponta. Apenas processos ou usuários portadores da autorização adequada (chaves simétricas do ambiente) poderão ler os payloads decriptados, honrando a Soberania do Dado (Artigo V).

## 3. Success Criteria
1. O desenvolvedor pode acompanhar a execução de ferramentas linha a linha pelo console (ou via WebSocket do `telemetry_api`) sem precisar de `print` isolado no código.
2. Erros de banco de dados ou Redis em `save_code_to_rag` não causam crashes silenciosos, mas geram entradas ricas de log indicando qual micro-serviço falhou.
3. O modelo Qwen2.5 no Nó 2 é capaz de invocar ferramentas via Bridge Redis após a configuração da variável `.env`, sem entrar em loop infinito de rejeição pelo Arquiteto.

## 4. User Scenarios
- **Scenario A (Falha de Banco de Dados)**: Dado que o PostgreSQL está desligado, Quando o Engenheiro chamar `save_code_to_rag`, Então o logger deve capturar e exibir um evento de "Falha na conexão com Postgres" imediatamente.
- **Scenario B (Inspeção de Rede)**: Dado que o orquestrador está rodando, Quando a vez for passada ao Arquiteto, Então o log do console deve avisar "Routing: Architect -> http://localhost:11434".

## 5. Assumptions & Open Questions
- **Assumption 1**: O `vitalia_events` (Redis Stream) com `maxlen=50000` influencia o armazenamento em RAM. Em cenários de loop infinito, as mensagens mais antigas são descartadas quando o limite é atingido, o que evita crash de memória, mas perde histórico. Ele **não** interrompe o loop por si só, sendo essencial o mecanismo do FR-006.
- **Assumption 2**: O TDD de `save_code_to_rag` atingirá o banco local real. Comandos de sanitização serão necessários após os testes para limpar os chunks gerados.
