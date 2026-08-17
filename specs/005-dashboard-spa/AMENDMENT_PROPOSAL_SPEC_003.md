# Proposta de Emenda (Amendment Proposal) para Spec 003

## Contexto da Emenda
A criação do Frontend SPA (Spec 005) baseado na estética "UI UX Pro Max" exige uma navegação fluida em diversas abas (como Queue Inspector e Node Inventory). 
Ao analisar o contrato de dados atual da **Spec 003** e a implementação em `telemetry_api.py`, identificou-se uma lacuna: não existem endpoints REST para buscar o estado estático/inicial de várias entidades, forçando o frontend a aguardar passivamente eventos de WebSocket, o que prejudica a User Experience inicial (Cold Start da UI).

## Proposta de Novos Contratos / Endpoints (Backend)

Para satisfazer os requisitos do Frontend (Spec 005), a Spec 003 deve ser atualizada para incluir os seguintes endpoints:

### 1. `GET /api/nodes`
- **Objetivo**: Retornar a lista completa de nós ativos presentes no `HSET vitalia:nodes:*`.
- **Contrato Esperado (JSON)**: Um array de objetos baseados em `DetailedNodeInventory`.
- **Por que o Frontend precisa?** Para popular a aba de "Node Inventory" instantaneamente ao carregar a página, antes do próximo pulso do Pub/Sub.

### 2. `GET /api/queues`
- **Objetivo**: Retornar a lista de streams/filas Redis ativas no sistema (ex: `vitalia:system:commands`, `vitalia:tool_requests:*`).
- **Contrato Esperado (JSON)**: Um array com os nomes das filas e suas contagens atuais (XINFO).
- **Por que o Frontend precisa?** Para criar a "Sidebar" de seleção no Queue Inspector.

### 3. `GET /api/queues/{queue_name}`
- **Objetivo**: Recuperar mensagens paginadas de uma fila Redis específica.
- **Contrato Esperado (JSON)**: Um array de `QueueMessagePayload`.
- **Por que o Frontend precisa?** Para o Queue Inspector exibir o histórico de eventos que já passaram pelo stream antes do usuário conectar o WebSocket.

---
**Status da Emenda**: Aguardando aprovação em conjunto com a Spec 005. Se aprovada, estes três endpoints serão implementados em `telemetry_api.py` antes do início do desenvolvimento do Frontend em React.
