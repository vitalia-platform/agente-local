<!-- AGENTS.md | Atualizado em: 01-07-2026 15:03:06(GMT-04:00) -->
# Regras Globais do Projeto

- **Melhoria (Rule):** Evitar o uso explícito da palavra de parada (`TERMINATE`) nos prompts e checklists de teste submetidos aos agentes, utilizando sinônimos (ex: "encerre o chat"), a fim de evitar gatilhos prematuros nas condições `TextMentionTermination` do AutoGen.
