<!-- AGENTS.md | Atualizado em: 12-08-2026 22:04(GMT-04:00) -->

# AGENTS.md — System Pointer (Vitalia Kit v0.4.0)

> [!WARNING]
> **POINTER FILE ONLY (Thin Client)**
> As tabelas locais de roteamento e a Constituição de Vitalia foram centralizadas no Kit Global (Decisão Arquitetural v0.4.0).
> Não armazene regras longas neste arquivo para evitar perda de foco durante a troca de modelos (Context Amnesia).

**Instruções Críticas para o Agente (Antigravity):**

1. **Roteamento Inteligente:** Se o usuário fizer um pedido em linguagem natural, acione a skill `/vitalia-route` para que ela classifique a intenção usando o Smart Router global.
2. **Constituição e Segurança:** Você DEVE ler e seguir o `architect-constitution.yaml` para regras críticas de processo. Nunca pule o SDD Pipeline.
3. **Execução de Skills:** As regras de comportamento estão embutidas dentro das próprias skills em `.agents/skills/`. Siga estritamente o `prompt` da skill acionada.

> O caminho global do kit é `~/.vitalia/kit`. Use-o para ler as regras (ex: `~/.vitalia/kit/rules/always-on/architect-constitution.yaml`).
