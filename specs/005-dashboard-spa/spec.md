<!-- 005-dashboard-spa.spec.md | Atualizado em: 30-07-2026 19:21:00(GMT-04:00) -->
# Especificação de Funcionalidade: Vitalia Dashboard SPA (Frontend)

**Data:** 30-07-2026
**Autor/Agente:** Antigravity (Architect)
**Dependência:** Spec 003 (Backend Node Manager)

## 1. Contexto e Objetivo (O Quê e Por Quê)
O painel de controle da Vitalia (Node Manager) atualmente é renderizado via arquivos HTML estáticos brutos servidos pelo backend. Para acompanhar a complexidade crescente das funcionalidades (como Queue Inspector e gráficos em tempo real) descritas na Spec 003, e para alcançar o padrão estético "Pro Max", precisamos desvincular o frontend.
O objetivo desta especificação é definir o comportamento da camada visual (Single Page Application) que consumirá as APIs e WebSockets do backend. Esta separação permite evoluir a UX de forma independente da orquestração de hardware.

## 2. Requisitos Funcionais
O que o software deve fazer de forma observável?
- [ ] FR-001: O sistema MUST prover uma interface de usuário no formato SPA (Single Page Application) baseada em navegação client-side.
- [ ] FR-002: O usuário poderá autenticar-se utilizando a "Master Password", e o token JWT MUST ser armazenado de forma segura no cliente para chamadas subsequentes.
- [ ] FR-003: O sistema MUST exibir um "Telemetry HUD" conectando-se ao WebSocket (`/ws/events`) para refletir métricas de inferência em tempo real.
- [ ] FR-004: O sistema MUST possuir uma tela dedicada "Node Inventory" que liste todos os nós da malha (baseado na descoberta da Spec 003).
- [ ] FR-005: O sistema MUST possuir uma tela de "Queue Inspector" que permita listar e auditar o payload de mensagens de filas específicas.
- [ ] FR-006: O sistema MUST disponibilizar o painel de Benchmark para rodar testes comparativos e atualizar o `.env` via chamadas de API REST.

## 3. Requisitos Não-Funcionais (Restrições)
Quais as regras de performance, segurança, ou aderência à Constituição do Arquiteto?
- [ ] NR-001 (UI/UX): A interface MUST seguir os guidelines estéticos premium (Glassmorphism fluido, Dark Mode absoluto) utilizando as famílias tipográficas DM Sans e Space Grotesk importadas via CDN.
- [ ] NR-002 (Performance): A latência de renderização das atualizações via WebSocket NÃO DEVE congelar a thread principal da UI (suportar frequências de 1Hz tranquilamente).
- [ ] NR-003 (Arquitetura): O build final do Frontend MUST ser exportado como artefatos estáticos (`dist/`) injetados em `vitalia-core/static/`, sem requerer um servidor NodeJS intermediário em produção (apenas o FastAPI atual).
- [ ] NR-004 (Contrato): O Frontend é estrito consumidor dos contratos definidos na Spec 003. Campos não previstos no contrato requerem emenda oficial no backend antes do uso.

## 4. Histórias de Usuário (User Stories)
**Como um** Engenheiro do Sistema, **eu quero** visualizar a telemetria ao vivo com uma estética polida **para que** eu consiga detectar gargalos cognitivamente com facilidade.
**Como um** Desenvolvedor, **eu quero** usar uma aba de Queue Inspector **para que** eu possa ler payloads JSON das filas do Redis de forma estruturada.
**Como um** Administrador, **eu quero** navegar entre abas do dashboard instantaneamente (sem reload da página) **para que** eu possa gerenciar modelos e configurações sem perder o contexto do log na tela.

## 5. Critérios de Aceite (Acceptance Criteria)
Condições estritas para considerar a funcionalidade concluída.
- [ ] SC-001: Dado que o usuário logou, quando acessar a aba de Inventory, então ele visualiza a tabela formatada (com gráficos de gauge) sem recarregar o navegador.
- [ ] SC-002: Dado que o usuário navega para a aba Queue Inspector, quando ele clica em uma fila, então os dados (payload JSON) são renderizados utilizando um viewer estruturado formatado.
- [ ] SC-003: Dado que o usuário abre o modal de Configurações, quando ele salva variáveis, então a requisição REST é feita com o Header Authorization JWT.

## 6. Fora do Escopo (Out of Scope)
O que NÃO será feito nesta etapa (para evitar scope creep).
- [ ] Modificações de regras de roteamento (LLM Routing) ou controle de concorrência Redis (que pertencem a outras specs).
- [ ] Reescrita do Backend. O backend permanecerá FastAPI, apenas provendo as rotas que o frontend consumirá.
