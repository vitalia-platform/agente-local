# Technical Research: Vitalia Dashboard SPA (Spec 005)

## Decisão: Stack de Frontend (Framework e Build Tool)
- **Escolhido**: React com TypeScript, utilizando Vite como bundler.
- **Justificativa**: React oferece o ecossistema mais maduro para aplicações SPA que exigem reatividade complexa (WebSockets, atualização em tempo real de gráficos e filas), alinhando-se à escalabilidade da Spec 003. TypeScript garante que os contratos de dados da Spec 003 (Backend) sejam rigidamente tipados no cliente, evitando erros silenciosos de payload. Vite proporciona build rápido e permite configurar a pasta de saída (outDir) diretamente para a pasta estática do backend (`vitalia-core/static`), mantendo a arquitetura de servidor único.
- **Alternativas**:
  - *Vanilla JS/HTML*: Rejeitado porque a manipulação manual de DOM se tornaria um espaguete insustentável ao implementar o Queue Inspector paginado e os gráficos de inventário de nós previstos na Spec 003.
  - *Vue.js*: Viável, porém a adoção de React foi preferida pela robustez do ecossistema e facilidade de integração com bibliotecas futuras, caso necessárias.

## Decisão: Design System e Estilização
- **Escolhido**: CSS Vanilla (CSS Modules) implementando o Design System do "UI UX Pro Max" (Glassmorphism, Dark Mode Nativo, fontes DM Sans e Space Grotesk via Google Fonts CDN).
- **Justificativa**: A restrição do sistema impede o uso de TailwindCSS (a menos que estritamente solicitado). CSS Vanilla/Modules garante independência total, estilização focada, isolamento por componente (evitando conflitos globais) e não injeta utilitários desnecessários no bundle final. A estética "Pro Max" elevará a percepção de valor e usabilidade do painel (Telemetry HUD e Queue Inspector).
- **Alternativas**:
  - *TailwindCSS*: Rejeitado por restrição de ambiente/preferência registrada.
  - *Styled Components*: Rejeitado para evitar sobrecarga de runtime de CSS in JS; CSS Modules resolve o isolamento de escopo sem overhead.

## Decisão: Integração Bidirecional API-First
- **Escolhido**: Consumo estrito de Contratos (Spec 003 Amendment).
- **Justificativa**: O frontend não ditará lógicas de negócio. Ele requisitará o estado através das APIs propostas na emenda da Spec 003 (`GET /api/nodes`, `GET /api/queues`) e hidratará a UI de forma assíncrona.
- **Alternativas**:
  - *Mockar dados no Frontend*: Rejeitado. Feriria a regra API-First e criaria falso positivo no desenvolvimento. O Backend deve fornecer os endpoints aprovados na emenda antes de o React começar a consumi-los.
