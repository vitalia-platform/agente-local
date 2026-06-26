<!-- README.md | Atualizado em: 26-06-2026 12:08:18(GMT-04:00) -->
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

Para inicializar o projeto no seu notebook (ou em uma máquina nova), você precisará primeiro baixar o **Kit de Agentes Global**, e depois ativá-lo na pasta deste projeto. Siga os dois passos abaixo no seu terminal:

**Passo 1: Instalação Global do Kit Vitalia**
Baixe os componentes do kit para a sua máquina (`~/.vitalia-spec`):
```bash
wget -qO- https://raw.githubusercontent.com/vitalia-platform/agente-local-spec-kit/main/scripts/bootstrap.sh | bash
```

**Passo 2: Ativação no Projeto Local**
Clone este repositório (`agente-local`), entre na pasta dele e execute o script para vincular o kit:
```bash
git clone git@github.com:vitalia-platform/agente-local.git
cd agente-local
bash ~/.vitalia-spec/scripts/install.sh
```

> **Aviso:** Antes de executar a instalação, certifique-se de já ter criado um repositório vazio no GitHub que servirá de **repositório de contexto** (ex: `revisao-[tema]-contexto`), pois a URL SSH será solicitada durante o processo.
