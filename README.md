# Vitalia Agente Local

Bem-vindo ao **Agente Local** da plataforma Vitalia. Este repositório contém a infraestrutura e os workflows que habilitam o *Spec-Driven Development* (SDD) guiado por IA, garantindo que todo código e configuração siga regras estritas de arquitetura e qualidade (incluindo segurança clínica).

## Objetivo

O objetivo deste projeto é atuar como um orquestrador local de desenvolvimento e engenharia auxiliada por IA. Ele aplica workflows (como `session-start`, `spec-specify` e `session-end`) para estruturar a comunicação com o LLM, garantir validações de arquitetura e orquestrar TDD de forma robusta, conectando times humanos e inteligência artificial num fluxo determinístico.

## Métodos

A arquitetura do Agente Local baseia-se em princípios sólidos:

1. **Spec-Driven Development (SDD):** Nenhuma linha de lógica de negócio é escrita sem que uma especificação prévia tenha sido aprovada pelo desenvolvedor.
2. **Contexto Descentralizado (Dual-Git):** A memória da Inteligência Artificial vive num repositório Git separado. Usamos estratégias de *sharding* de máquinas e um protocolo de `session-consolidate` para gerenciar concorrência quando desenvolvedores ou agentes em várias máquinas colaboram no mesmo projeto.
3. **Guardrails Socráticos e Clínicos:** O workflow de `brainstorming` extrai pontos cegos ativamente, enquanto gateways clínicos (Medical Gate) garantem checagens restritas para specs no domínio da saúde.
4. **Test-First Rigoroso:** Obriga que os testes (fase *Red*) sejam aprovados pelo usuário antes da escrita da implementação final (*Green*).

## Instalação

Para inicializar o Vitalia Kit localmente e vincular este agente ao seu repositório de contexto, basta executar o seguinte comando em seu terminal. Ele fará o download e rodará o script de setup automático de dependências, symlinks e validações:

```bash
wget -qO- https://raw.githubusercontent.com/vitalia-platform/agente-local/main/.specify/scripts/install.sh | bash
```

> **Aviso:** Antes de executar a instalação, certifique-se de já ter criado um repositório vazio no GitHub que servirá de **repositório de contexto** (ex: `revisao-[tema]-contexto`), pois a URL SSH será solicitada durante o processo.
