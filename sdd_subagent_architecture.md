<!-- sdd_subagent_architecture.md | Atualizado em: 15-08-2026 08:45:00(GMT-04:00) -->
# Arquitetura SDD: Fluxo Multi-Agent, Sub-Agent Hooks e Dynamic Domain Routing

Conforme as melhores práticas atuais de *Agentic Software Engineering* e o fluxo base do repositório `github/spec-kit`, a forma correta de ancorar (grounding) um agente em dados reais sem causar poluição de contexto ("Vibe Coding") é combinar **Sub-Agent Hooks** com uma estrutura de **Dynamic Domain Routing (Roteamento Dinâmico de Domínios)**. 

A especificação passa a ser a "fonte da verdade" e o código apenas a sua expressão final (paradigma de **Executable Specifications**).

---

## 0. O Papel do Spec-Kit e as Interações Locais

A análise profunda da metodologia do `github/spec-kit` revela que a especificação não é um documento estático, mas o *coração do desenvolvimento iterativo* (1 -> 1' -> 2). No ecosssistema local da Vitalia, existem workflows que já suportam esse ciclo de refinamento contínuo:
- **`analyze.toml`**: Atua como um Quality Assurance contínuo, fazendo uma varredura cruzada (read-only) entre `spec.md`, `plan.md` e `tasks.md` em busca de gaps ou violações (incluindo *Medical Gates* e *Science Reviews*). Ele garante o que o spec-kit chama de "Consistency Validation".
- **`clarify.toml`**: Refina ambiguidades de forma interativa.
- **Melhoria proposta pelo Spec-Kit**: A pesquisa de bibliotecas, compatibilidade e segurança não é feita "de cabeça". **Agentes Pesquisadores coletam contexto real**. Integrar essa filosofia significa que, em vez do Arquiteto tentar adivinhar a tecnologia, ele a delega.

### O Novo Grounding Registry e o Validation Schema
O arquivo `grounding-domains.yaml` evolui de uma lista plana para um **Grounding Registry** (Control Plane):
```yaml
domains:
  python_packages:
    authoritative_source: "pypi.org"
    validation_schema: 
      type: "object"
      properties:
        package_name: { type: "string" }
        stable_version: { type: "string" }
        breaking_changes: { type: "boolean" }
      required: ["package_name", "stable_version"]
```
**Onde está esse schema?** Ele será definido estruturalmente dentro do próprio `grounding-domains.yaml` (usando JSON Schema embutido). O Orquestrador roteia a tarefa para o Sub-Agente Pesquisador e exige que o output retorne num JSON/formato que case com o schema, forçando o retorno estruturado e sem "falas".

---

## 1. Fase de Descoberta: `/vitalia-brainstorming`

- **Ambiente Mapeado (Pre-Flight Scan):** Um hook passivo lê a infraestrutura local (ex: `.env`, `docker-compose.yml`, `package.json`, `.venv`) e as especificações da pasta `docs/`.
  - **Mitigação de Context Overload (RAG via pgvector):** Para não estourar os tokens, o ambiente é indexado em um banco vetorial local (pgvector). O arquiteto apenas "consulta" restrições. Para lidar com mudanças nas specs, adotamos uma estratégia de *Sync/Cleanup* baseada em *Content Hash* (atualizando o vetor apenas se o arquivo mudou) e rodamos uma rotina "Janitor" no encerramento da sessão (`session-end`) para dar `DELETE CASCADE` em vetores órfãos.
- **Ação e Trade-offs:** Baseado na intenção do usuário e no ambiente, o agente sugere caminhos, cruzando desejos com limitações práticas.
- **Artefato Vivo (Running Summary):** Ao final de cada iteração, é gerada uma tabela com:
  1. Decisões tomadas
  2. O racional ("Por quês")
  3. Fontes ancoradas na web.
  > **Proteção Anti-Alucinação:** O Running Summary **NÃO PODE** usar o conhecimento interno do modelo. As fontes e links apresentados devem obrigatoriamente ter sido acessados na web (com links **testados** e clicáveis), poupando o usuário de verificar URLs mortas. Se o modelo não pôde pesquisar ativamente, ele deve delegar a busca ao Sub-Agente ou marcar o item como não verificado (obedecendo a regra `grounding.md`).

---

## 2. Fase de Especificação e Clarificação: `spec-specify` e `clarify`

- **Leitura Passiva Contínua:** O `/vitalia-spec-specify` consome o *Running Summary* e reavalia passivamente a infra local para gerar os FRs e SCs sem gerar dívida técnica impossível.
- **O Papel do Clarify:** Como um iterador de requisitos (citado no Spec-Kit), ele extrai do usuário exatamente o que é necessário para tapar buracos operacionais. Ele sempre ancora dúvidas tecnológicas via Sub-Agente antes de sugerir a "Recomendação A".

---

## 3. Fase de Arquitetura: `/vitalia-spec-plan` e a Delegação Ativa

- **Fase 0 - O Hook de Pesquisa (Sub-Agent):** O `spec-plan` pausa ativamente antes do planejamento para que o Agente Pesquisador consolide o `research.md`.
- **Comportamento do Arquiteto (A Regra da Delegação):** 
  O Agente Arquiteto **não é proibido** de realizar pesquisas ou ter conhecimento, mas ele tem a **obrigação de DELEGAR sempre** qualquer pesquisa técnica (versões, dependências, APIs, quebras de contrato) para o Sub-Agente Pesquisador via Grounding Registry. Se ele precisa de uma informação, ele a solicita; ele não tenta adivinhar. O Sub-Agente é sua interface única com a web.
- **Aprovação Humana (HITL):** O dicionário de decisões validado pela web é submetido à revisão do usuário. O plano só é traçado (`plan.md` e `tasks.md`) após autorização.

---

## 4. Fase de Verificação (Novo Sub-Agent) e Implementação

- **Novo Sub-Agent: Policy & Task Verifier (Compliance Checker):**
  Antes de iniciar a implementação, imediatamente após a geração do `tasks.md` (ou convocado manualmente), um Sub-Agente independente entra em cena.
  - **Estratégia Adotada (Híbrida: Código + LLM Leve):** Um script Python extrai as tarefas isoladamente. Regras rígidas são checadas por código determinístico. Regras subjetivas (como Medical Gate) são disparadas como *micro-avaliações* para um modelo leve local (recomendado: `qwen2.5-coder:7b`, devido à sua excelência comprovada em lógica estruturada e baixo consumo de VRAM). O modelo não lê a lista toda, ele avalia estritamente "1 Tarefa vs 1 Regra" por inferência.
  - **Objetivo:** Garantir que nenhuma tarefa fira princípios de arquitetura, segurança ou grounding. Se violar, ele barra a transição para o `spec-implement` e devolve a tarefa para ajuste.
- **Verificação via `analyze.toml`:** Garante que o plano cobre todos os requisitos.
- **A Implementação (`/vitalia-spec-implement`):** Foco puro em cumprir o `tasks.md`.
- **Sub-Agent Revisor (Critic):** Após a escrita do código, garante a conformidade com as "Executable Specifications".
