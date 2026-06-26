<!-- vitalia-dashboard.spec.md | Atualizado em: 26-06-2026 12:08:18(GMT-04:00) -->
<!-- vitalia-dashboard.spec.md | Criado em: 25-06-2026 -->

# Especificação de Funcionalidade: Vitalia Dashboard & Telemetry API (Event-Driven Control Plane)

**Data:** 25-06-2026
**Autor/Agente:** Antigravity (Arquiteto)

## 1. Contexto e Objetivo (O Quê e Por Quê)
O projeto Vitalia requer visibilidade em tempo real sobre a execução dos agentes e o estado da infraestrutura de hardware distribuída. O atual `telemetry_api.py` fornece apenas uma leitura estática de VRAM. O objetivo desta spec é evoluir esse script para um **Control Plane** completo: um backend FastAPI que fornece um frontend visualmente premium, recebendo atualizações dinâmicas e contínuas sobre tokens processados, progresso de chunks no RAG, estimativa de tempo e uso de GPU. Adicionalmente, o painel servirá como hub de controle, permitindo iniciar, parar e reiniciar serviços da infraestrutura, exigindo uma camada robusta de segurança.

## 2. Requisitos Funcionais
- [ ] O sistema deve implementar uma arquitetura **Event-Driven**: Os agentes (Nó 1) enviarão métricas operacionais para filas específicas no Redis (Streams ou Pub/Sub).
- [ ] O `telemetry_api.py` (atuando como Backend Bridge) deve assinar (subscribe) essas filas e repassar os dados ao Frontend através de **WebSockets** ou Server-Sent Events (SSE).
- [ ] O Frontend deve ser servido pelo próprio FastAPI (rotas estáticas) para eliminar a necessidade de um servidor Node.js intermediário.
- [ ] O Dashboard deve exibir dados em **Tempo Real** sem necessidade de refresh (F5):
    - Uso de GPU/VRAM de cada Nó (Nó 1 e Nó 2).
    - Métricas de inferência: Tokens processados por turno.
    - Status do RAG: Número de chunks salvos.
    - Métricas temporais: Tempo decorrido (Elapsed) e Tempo Estimado (ETA) baseado nas tarefas da sprint.
- [ ] O Dashboard deve atuar como **Painel de Controle Ativo**, possuindo botões com as ações: Start, Stop, Restart e Kill.
- [ ] As rotas de controle devem se integrar ao Docker (via `docker` SDK for Python) para reiniciar containers ou gerenciar processos críticos via `psutil`.
- [ ] O Dashboard deve possuir uma **Tela de Configurações (Settings Panel)**:
    - Permitir a edição visual das configurações base (ex: mapeamento do `.env`, flags do Pub/Sub, endpoints).
    - Exibir a lista completa de LLMs disponíveis (via `/api/tags` do Ollama) em cada Nó.
    - Possuir um recurso **"Test & Benchmark Connections"** que, ao ser clicado, pinga todos os nós, afere latência de rede, tempo de carga de modelo na VRAM e tempo de inferência (Tokens/sec).
    - Permitir **Salvar & Aplicar** as configurações, o que regravará os arquivos e acionará o reinício dos processos/containers afetados automaticamente de forma segura (Graceful Restart).

## 3. Requisitos Não-Funcionais (Restrições e Estética)
- [ ] **Estética Premium (Art. IX UI/UX):** O painel deve seguir padrões de design moderno:
    - **Dark Mode** como padrão primário.
    - Paletas harmoniosas (acentos em Neon para identificar estados dos nós).
    - Elementos com **Glassmorphism** (fundos semi-transparentes com blur).
    - **Micro-animações**: Interações fluidas e barras de progresso animadas que reagem instantaneamente aos dados do WebSocket.
- [ ] **Tecnologias de Frontend:** Uso de Vanilla CSS ou TailwindCSS. Zero dependências pesadas (como React/Next.js), mantendo o bundle ultraleve.
- [ ] **Segurança (Autenticação Obrigatória):** Como o Dashboard pode emitir comandos operacionais no servidor (Kill/Restart), as rotas de API e WebSocket **devem ser protegidas** por autenticação via Token (Bearer JWT ou similar). Nenhum comando pode ser aceito sem o token válido na rede local.
- [ ] **Topologia Distribuída:** Cada nó (Nó 1 e Nó 2) rodará sua própria instância do `telemetry_api.py` para observar seus recursos locais, e o frontend pode centralizar as leituras via chamadas cruzadas autenticadas.

## 4. Histórias de Usuário (User Stories)
**Como** [Operador do Sistema Vitalia], **eu quero** [ter uma visão unificada e em tempo real do uso da VRAM e dos tokens processados] **para que** [eu saiba exatamente o esforço cognitivo do orquestrador sem olhar terminais].
**Como** [Operador do Sistema Vitalia], **eu quero** [que a interface seja premium, dinâmica e com respostas imediatas] **para que** [eu não precise recarregar a página e a experiência de uso seja fluida].
**Como** [Administrador do Vitalia], **eu quero** [ter uma tela de Configurações com testes de conexão e benchmark] **para que** [eu possa gerenciar todo o ecossistema (listar modelos, alterar variáveis, reiniciar serviços) diretamente pelo painel central, sem precisar editar arquivos de texto ou rodar scripts].
**Como** [Engenheiro de Infra], **eu quero** [poder reiniciar o motor de inferência (Ollama) ou o orquestrador com um clique seguro] **para que** [eu possa resolver falhas rapidamente sem abrir um terminal SSH para o Nó 2].

## 5. Critérios de Aceite (Acceptance Criteria)
- [ ] A página principal do Dashboard carrega via rota do FastAPI (ex: `http://localhost:8000/dashboard`).
- [ ] Uma conexão WebSocket é estabelecida com sucesso entre o browser e a API.
- [ ] Os componentes visuais atualizam dinamicamente a cada N milissegundos conforme mensagens chegam pelo Redis/WebSocket, sem refresh da página inteira.
- [ ] Acessar um endpoint de ação (ex: Restart) sem o Token Bearer correto retorna `HTTP 401 Unauthorized`.
- [ ] O design implementa estritamente os guias visuais: Dark mode, glassmorphism e animações.

## 6. Fora do Escopo
- [ ] Controle granular de parâmetros finos de LLMs pela interface (apenas operações de ciclo de vida de processo são permitidas).
- [ ] Armazenamento histórico infinito de logs no banco de dados (o Dashboard exibe estado real e tendências de curto prazo via Redis).
