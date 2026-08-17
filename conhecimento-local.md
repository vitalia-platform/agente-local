# Base de Conhecimento Local (Agente Local)

## 1. Orquestração Híbrida e Hardware (Dois Nós)
O projeto resolve a falta de VRAM local distribuindo as cargas:
- **Nó 1 (Notebook/CPU)**: Executa o Agente Arquiteto com modelos leves (`llama3.2:3b`). Roda Motor central, Redis e RAG.
- **Nó 2 (GPU Dedicada)**: Executa o Agente Engenheiro com modelos maiores (`qwen2.5-coder:7b`) focando em sintaxe e código.
- Configuração de hardware dinâmico via `.env` (`NO1_TOOL_CALLING_NATIVE` vs `NO2_TOOL_CALLING_NATIVE`).
*Referência: docs/ARCHITECTURE.md*

## 2. Tool Bridge e Redis Streams
Devido a limitações do framework AutoGen ao rotear respostas que usam ferramentas (Tool Calling) antes de injetar os resultados, implementamos um Wrapper:
- O **VitaliaOllamaClient** bloqueia a execução da thread (`asyncio.Event`), envia a solicitação de ferramenta à fila `vitalia:tool_requests` no Redis, aguarda a resposta do worker e só então entrega ao AutoGen.
*Referência: docs/ARCHITECTURE.md, docs/ONBOARDING.md*

## 3. Observabilidade em Tempo Real (Dashboard de Vidro)
Para evitar que o orquestrador multi-agentes atue como uma caixa preta assíncrona, todos os eventos do LLM são capturados.
- Eventos são criptografados (`Fernet`) e injetados na fila `vitalia_events`.
- Uma API em FastAPI consome e despacha para um Dashboard Web via WebSockets.
- Permite detectar raciocínios incorretos (arquiteto quebrando a spec vs. engenheiro desobedecendo).
*Referência: docs/ARCHITECTURE.md, docs/ONBOARDING.md*

## 4. Mecanismo Anti-Loop e Estabilidade
Agentes que iniciam debates circulares estocásticos sofrem "Termination".
- Usamos limites firmes: `MaxMessageTermination(max_messages=10)` acoplado à injeção forçada de `TextMentionTermination("__VITALIA_ABORT__")`.
*Referência: docs/ARCHITECTURE.md*

## 5. RAG e Memória em Duas Velocidades
Além da Memória Tier de Contexto e Pipeline SDD, há armazenamento em duas vias:
- **Hot Cache (Redis)**: Memorização em milissegundos do que acabou de ser escrito (`vitalia:hot_rag:*`).
- **Cold Storage (PostgreSQL + pgvector)**: Modelos vetorizados via `nomic-embed-text` rodando persistência semântica.
*Referência: docs/ARCHITECTURE.md, docs/ONBOARDING.md*

## 6. Medical Gate (Domínio de Saúde)
O sistema contém instâncias de atuação clínica restrita.
- Se uma Spec tocar em parâmetros de saúde (ex: dosagens, IMC), ela invoca o `vitalia-medical-gate`.
- Sem uma seção de "Critérios de Aceite Clínicos", o Agente Engenheiro recebe `TERMINATE` automático e o código é rejeitado.
*Referência: docs/ARCHITECTURE.md*
