# Base de Conhecimento Global (Vitalia Kit)

## 1. Arquitetura de Memória e Contexto (3 Tiers)
A gestão de memória do Kit Vitalia segue uma arquitetura moderna para LLMs, dividida em três camadas para evitar poluição de contexto e perda de rastreabilidade:
- **Tier 0 (Working Memory)**: Buffer efêmero da sessão ativa, some no final da sessão.
- **Tier 1 (Session State)**: Progresso recente. Arquivos: `SESSION_STATE.md` (estado ativo, feature, P0, 300 tokens máximo). Atualizado pelo `session-end`.
- **Tier 2 (Long-Term Memory)**: Conhecimento permanente e de dogfooding. Arquivos: `DECISIONS.md` (ADRs compactos, append-only) e `LEARNINGS.md` (Aprendizados divididos em tracks `[KIT]` e `[PROJETO]`).
*Referência: context-management-analysis.md*

## 2. SDD (Spec-Driven Development) e Fluxo Socrático
Todo fluxo deve respeitar as fases rígidas de estruturação antes da execução: `Brainstorming -> Specify -> Plan -> Tasks -> Implement`.
- **Erro Estrutural Corrigido**: Inserções aditivas em arquivos de prompt `.toml` modificam o comportamento estocástico do modelo. Guard Rails de comportamento devem vir antes dos de conteúdo.
- **Regra Inviolável (Pausa Socrática)**: Workflows como `/vitalia-brainstorming` nunca geram código ou manipulam arquivos na primeira iteração. Eles exigem avaliação de Prós/Contras, identificação de blind spots e autorização humana antes de avançar.
*Referência: Correção estrutural.md*

## 3. Agnosticismo de Paths e Thin Client
Os arquivos locais de um projeto (`.agents`, `.gemini`) devem ser puramente shims ou "thin clients". A lógica real vive no kit global.
- Paths como `.specify/memory/` ou `~/.vitalia-spec/` não devem ser "hardcoded" em prompts. Eles devem ser variáveis (`{{VITALIA_DIR}}`) resolvidas dinamicamente durante a instalação (`install-project.sh`).
*Referência: epic-kit-v040-sdd-integration-v3.md*

## 4. Presets em vez de Múltiplos Formatos
Para domínios específicos (Software, Pedagógico, Clínico), o kit abandonou a criação de múltiplos arquivos de spec (ex: `blueprint.spec.md`, `medical-gate.spec.md`). Em vez disso, adota-se um fluxo único de pipeline (`/vitalia-spec-specify`) utilizando o mecanismo de **Presets** para modular as seções da especificação em tempo de execução.
*Referência: epic-kit-v040-sdd-integration-v3.md*
