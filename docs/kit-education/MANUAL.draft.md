# Manual Educacional: Spec-Driven Development (SDD) com Vitalia Kit v0.4.0

Bem-vindo ao manual educacional de uso da metodologia SDD no ambiente local. Este documento reúne as principais teorias de especificação, dicionário de termos, lógicas do fluxo e o "porquê" de cada fase de planejamento antes da codificação.

---

## 1. Dicionário de Termos e Marcadores de Especificação

Durante o fluxo SDD, você notará a presença de expressões-chave entre asteriscos duplos nas `User Stories`. Estes marcadores são vitais para as heurísticas do agente. Eles nunca devem ser negligenciados, pois "ativam" validações cognitivas no prompt subjacente do LLM.

### Estrutura de User Story (Priorização e MVP)

- `**Why this priority**`: Um campo semântico obrigatório. Obriga a justificativa de negócio do porquê esta história (P1, P2) tem tal nível de importância. O Agente verifica isso para evitar que "tudo seja urgente".
- `**Independent Test**`: Um marcador crítico do SDD. Garante a concepção modular da feature, exigindo que a funcionalidade possa ser testada em isolamento (MVP incremental), sem depender de lógicas externas acopladas.

### Cenários de Aceitação (Gherkin BDD)

- `**Acceptance Scenarios**`: O bloco onde descrevemos as interações de sistema baseadas na linguagem Gherkin (Behavior-Driven Development).
  - `Given`: Dado um [estado inicial / pré-condição] do sistema.
  - `When`: Quando ocorre um [evento ou gatilho / ação do usuário].
  - `Then`: Então observamos o [resultado testável / alteração de estado esperada].
  > *Regra Ouro*: Se você não consegue descrever o `Then` com precisão, a funcionalidade ainda está ambígua e precisa retornar para o `/vitalia-clarify`.

### Requisitos Técnicos (RFC 2119)

- `**FR-xxx** (Requisitos Funcionais)`: Especificam *o que* o sistema fará. Usamos a notação semântica:
  - `MUST`: Obrigatório, não-negociável. A release não sai sem isto.
  - `SHOULD`: Altamente recomendado. Podem haver ressalvas técnicas, mas devem ser fortemente justificados se não entrarem.
  - `MAY`: Agrega valor mas não bloqueia a funcionalidade core.
- `**SC-xxx** (Critérios de Sucesso)`: Métricas agnósticas à tecnologia (ex: tempo de latência, número de registros processados por minuto) que balizam a qualidade do requisito.

---

## 2. A Teoria do Fluxo Pipeline SDD

O fluxo do Vitalia Kit v0.4.0 é rígido. Nenhum artefato avança sem a aprovação do usuário. O pipeline funciona ancorado em três perguntas: **O Quê**, **Como** e **Quando**.

### Fase 1: Especificação (O Quê)
**Comando:** `/vitalia-spec-specify`
- A partir de uma conversa, gera-se o `spec.md`.
- Ele traduz o seu pedido em lógicas estritas (User Stories, FRs, SCs, Given/When/Then).
- *Artefato Principal:* `spec.md`

### Fase 2: Planejamento Arquitetural (Como)
**Comando:** `/vitalia-spec-plan`
- Lê o `spec.md` aprovado e investiga o estado atual do repositório. 
- Mapeia "o que mudar", propondo a stack técnica e a estrutura de diretórios.
- *Artefatos Gerados:* 
  - `plan.md`: Decisões técnicas.
  - `research.md`: Notas, explorações de viabilidade, e limitações analisadas durante a fase de planejamento.
  - `contracts/`: Caso se alterem APIs ou interfaces, os contratos são firmados primeiro aqui antes de se programar as classes.

### Fase 3: Divisão de Tarefas Atômicas (Quando/Quem)
**Comando:** `/vitalia-spec-tasks`
- Fragmenta o `plan.md` em tarefas atômicas executáveis (`tasks.md`).
- Formato `T001 [P] [US1]`: Estabelece a dependência estrita para que o Agente ou o Dev humano possa dar *check* ordenado.

### Fase 4: Implementação 
**Comando:** `/vitalia-spec-implement`
- O Agente Coder assume o controle, lendo o `tasks.md` aprovado, e executa o código. 
- Ele atualiza seu progresso `[X]` a cada task concluída e valida contra o `Acceptance Scenarios` original.

### Fase 5: Consistência (Reconciliação Contínua)
**Comando:** `/vitalia-converge`
- Usado para auditar desvios. Compara o código real gerado com o prometido em `spec`, `plan` e `tasks`. Pode ser acionado periodicamente para dogfooding do pipeline SDD.
