<!-- Contratos_Comportamentais.md | Atualizado em: 15-08-2026 08:45:00(GMT-04:00) -->
# Metodologia e Contratos Comportamentais (Sub-Agent Hooks e Grounding Registry)

Este documento estabelece os contratos comportamentais rigorosos para a modificação dos workflows da Vitalia. A abordagem de "operação de texto" (apenas inserir regras no prompt) foi abandonada em favor da **Engenharia de Comportamento**, baseada em *Separation of Concerns* (Sub-Agentes) e roteamento dinâmico via *Grounding Registry*, com forte inspiração nos princípios de *Specification-Driven Development* (SDD).

## 1. Regras de Design e Modificação de Workflows

Para evitar o "Interleaving Problem" (alucinações geradas por forçar o agente a pesquisar e codificar simultaneamente), adotamos as seguintes regras para a reescrita dos arquivos `.toml`:

1. **A Regra de Delegação Contínua:** O Agente Arquiteto **não é proibido** de pesquisar, e não deve fingir que não sabe das coisas. Porém, ele tem a obrigação comportamental de **SEMPRE DELEGAR** a pesquisa de domínios restritos (versões, dependências, etc.) para o Sub-Agente Pesquisador via `hooks.before` ou de forma assíncrona, usando-o como sua interface formal de validação com a realidade.
2. **Leitura Passiva de Ambiente:** Workflows de planejamento devem incluir instruções claras para consultar o estado atual (`.env`, `docker-compose.yml`, `package.json`, `.venv`, e `docs/`). Para evitar *context overload*, o arquiteto utilizará a busca vetorial local (RAG via `pgvector`), delegando a limpeza de índices antigos (stale documents) para a fase de `session-end`.
3. **Respeito ao Contrato de Interação:** O formato da resposta (output) deve respeitar a fase do SDD. O Brainstorming produz texto e um *Running Summary*; o Plan exige interrupção (HITL) após a pesquisa, antes da elaboração do plano.
4. **Submissão ao Grounding Registry e Validação:** Qualquer busca técnica deve obedecer às regras de validação estruturadas no `grounding-domains.yaml` (agora elevado a Registry).

---

## 2. Contratos Comportamentais por Workflow

> ⚠️ Nenhuma edição nos arquivos `.toml` será feita antes da aprovação final destes contratos.

### 2.1 Workflow: `brainstorming.toml`
- **O que o usuário vê (Experiência):** Ao propor uma ideia, o agente analisa a infraestrutura local, alerta sobre conflitos, propõe trade-offs técnicos e, ao final da resposta, exibe um "Resumo Contínuo" (Running Summary) das decisões, justificativas e fontes. Termina com uma pergunta socrática.
- **Propriedades a Preservar:** 
  - Proibição de gerar output executável (código).
  - Obrigatoriedade da pausa socrática.
- **Comportamento Esperado Após a Modificação:**
  - Inclusão do "Scan de Ambiente" (instruindo a leitura de configs).
  - A fase final de "Output: Running Summary" **exigirá** a inserção de *links testados e validados* obtidos exclusivamente da web. A restrição comportamental bloqueará o uso de conhecimento base do modelo na composição das fontes desta tabela.
  - A pesquisa ativa ocorrerá via delegação ao Sub-Agente.

### 2.2 Workflow: `spec-specify.toml`
- **O que o usuário vê (Experiência):** O agente gera a especificação formal (`spec.md`) cruzando a intenção validada no Brainstorming com as limitações reais do ambiente. A especificação se torna a interface primária (Executable Specifications).
- **Propriedades a Preservar:** 
  - Geração estruturada de FRs (Functional Requirements) e SCs (Success Criteria).
- **Comportamento Esperado Após a Modificação:**
  - Inserção da regra de Scan Passivo de Ambiente.
  - Integração semântica com o fato de que este artefato será iterado futuramente (1 -> 1' -> 2), abandonando a visão de que specs são apenas guias descartáveis.

### 2.3 Workflow: `clarify.toml` e `analyze.toml` (Consistency Validation)
- **O que o usuário vê (Experiência):** O `clarify` aponta lacunas e faz 5 perguntas cirúrgicas. O `analyze` realiza o pente fino de qualidade antes da implementação.
- **Comportamento Esperado Após a Modificação (`clarify`):**
  - O prompt integrará um direcionamento absoluto para a delegação: o agente **sempre usará** o Sub-Agente Pesquisador para sanar dúvidas tecnológicas no Grounding Registry antes de sugerir a "Recomendação A" ao usuário.
  - A integração de respostas na spec é imediata, apoiando a evolução contínua da mesma.

### 2.4 Workflow: `spec-plan.toml`
- **O que o usuário vê (Experiência):** Ao invocar o plano, o sistema "pausa". O Pesquisador entrega o `research.md` e o Dicionário de Decisões via web. O usuário aprova, e só então o plano final é escrito.
- **Propriedades a Preservar:** 
  - Passagem obrigatória pelo Constitution Check.
- **Comportamento Esperado Após a Modificação:**
  - O Arquiteto será condicionado pela **Regra de Delegação**: ele recebe a ordem de *nunca* tentar inventar ou buscar de memória as versões ou dependências. Ele precisa delegar a confecção do `research.md` (Fase 0) ao Sub-Agente.
  - O Arquiteto consumirá o cache confiável do Pesquisador e gerará o `plan.md` em harmonia com o `analyze.toml`, assegurando que todos os requisitos da fase anterior encontrem vazão nas tarefas.

### 2.5 Workflow: `task-verifier.toml` (Novo Sub-Agent de Compliance)
- **O que o usuário vê (Experiência):** Após a criação das tarefas (`tasks.md`), mas antes do implementador escrever o código, o sistema aciona silenciosamente (ou ativamente pelo usuário) um verificador de compliance.
- **Propriedades a Preservar:** 
  - Análise profunda baseada *exclusivamente* nas regras contidas na pasta `always-on` do kit.
  - Bloqueio imediato da etapa de implementação caso haja violação.
- **Comportamento Esperado:**
  - O verificador opera num Padrão Híbrido: script Python + inferência leve. O Agente não tenta ler o arquivo inteiro de uma vez; o script quebra o arquivo em tarefas isoladas e envia perguntas binárias (ex: "A Tarefa T001 viola a regra de Grounding?") para o LLM (`qwen2.5-coder:7b`). Se a verificação falhar, ele barra a transição, impedindo que o programador inicie o trabalho.

### 2.6 Atualizações Estruturais Gerais
- Migração de `grounding-domains.yaml` para o formato "Grounding Registry".
- Inserção e manutenção rigorosa de selo temporal (`<!-- nome_arquivo.ext | Atualizado em: ... -->`) em todos os arquivos modificados na sessão, zelando pela auditoria estipulada pela Constituição da Vitalia.
