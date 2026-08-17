# Spec-Driven Development (SDD) Onboarding

Este diretório contém os guias educacionais e os rascunhos para adoção do Spec-Driven Development com o **Vitalia Kit v0.4.0**.

## Como começar

A transição para o SDD pode parecer burocrática à primeira vista, mas o objetivo é reduzir a ambiguidade e separar o **planejamento** da **execução de código**, reduzindo significativamente o retrabalho.

1. **Leia o Manual:** Antes de usar o Kit, compreenda as lógicas e o dicionário de marcadores lendo o `MANUAL.draft.md` neste diretório.
2. **Entenda o Fluxo:**
   - Comece sempre com `/vitalia-spec-specify` para modelar a intenção.
   - Prossiga com `/vitalia-spec-plan` para arquitetar a solução técnica.
   - Avance para `/vitalia-spec-tasks` para quebrar as decisões técnicas em um checklist (TODO).
   - Somente após todos esses passos estarem claros e aprovados, inicie a codificação com `/vitalia-spec-implement`.

## Para Operadores do Kit

Sempre que vir marcadores como `**Why this priority**` ou `**Acceptance Scenarios**`, saiba que não são simples decorações visuais de Markdown. O sistema de agentes possui instruções de sistema (System Prompts) que os utilizam como heurísticas estritas para validar e recusar fluxos ambíguos. 

Se um cenário `Then` no seu spec não pode ser testado por uma máquina ou um QA de forma inequívoca, o agente está treinado para rejeitar o avanço das tarefas!
