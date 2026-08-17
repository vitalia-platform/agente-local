# Specification: Migração do Orquestrador para o Kit v0.4.0

**Status**: ⏳ AGUARDANDO APROVAÇÃO
**Preset**: software

---

## 1. Contexto e Objetivo (O Quê e Por Quê)
O código fonte do orquestrador atual (`vitalia-core`) foi construído com base em convenções antigas (ex: uso de pastas `.specify/` e leitura de arquivos Markdown brutos para skills). Com o lançamento do novo Vitalia Kit v0.4.0, a infraestrutura global mudou (agora baseada em metadados `.toml` e diretórios `.vitalia/` e `.agents/`).
O objetivo desta feature é adequar o código do orquestrador para interoperar perfeitamente com os novos padrões do Kit, permitindo que as skills leiam metadados avançados (TOML) e que os processos de CLI/bash acompanhem o estado do sistema corretamente, sem causar quebra na execução dos agentes.

---

## 2. Requisitos Funcionais e Não-Funcionais

### Requisitos Funcionais (FR-xxx)
- **FR-001**: O sistema **MUST** buscar configurações dinâmicas de diretório a partir da raiz do projeto, abandonando caminhos fixos inseridos diretamente no código-fonte.
- **FR-002**: A funcionalidade de carregamento de skills dinâmicas **MUST** fazer o parse nativo do formato TOML, garantindo que os agentes LLM recebam apenas o campo pertinente (ex: `prompt`), filtrando os metadados sistêmicos.
- **FR-003**: O sistema de sincronização de estados da sprint **MUST** possuir alta resiliência, gravando o estado em disco de forma autônoma caso o servidor Redis primário esteja indisponível.

### Critérios de Sucesso (SC-xxx)
- **SC-001**: Execuções do orquestrador em diferentes diretórios ou máquinas devem rodar perfeitamente sem falhas de "File Not Found".
- **SC-002**: O agente deve consumir menos tokens ao carregar uma skill TOML, recebendo apenas o bloco de prompt, sem poluição de hooks ou variáveis.
- **SC-003**: O arquivo `pipeline.json` deve ser criado imediatamente se o Redis falhar durante um update de sprint.

---

## 3. User Stories & Acceptance Scenarios

### User Story 1 - [Gerenciamento Dinâmico de Diretórios] (Priority: P1)
Como Desenvolvedor do Projeto, quero que o orquestrador resolva os caminhos dinamicamente para que eu não precise alterar o código fonte cada vez que o Kit global mudar a estrutura de pastas.

**Why this priority**: Evitar quebra da aplicação durante migrações de infraestrutura (P1).

**Acceptance Scenarios**:
1. **Given** que o diretório base do projeto foi alterado
2. **When** o orquestrador inicia e aciona o módulo de Logs
3. **Then** os shards são gravados na pasta `.vitalia/memory` correspondente à nova raiz, sem erros.

### User Story 2 - [Consumo Inteligente de Metadados TOML] (Priority: P1)
Como Agente Orquestrador (Engenheiro), quero receber apenas as instruções relevantes das Skills, sem precisar ler e interpretar metadados de hooks e transportes do TOML, economizando meu contexto de raciocínio.

**Why this priority**: Tokens de LLM são escassos, e enviar metadados irrelevantes para o prompt gera alucinações (P1).

**Acceptance Scenarios**:
1. **Given** um arquivo `.toml` contendo `[hooks]`, `[transport]` e um `prompt`
2. **When** eu chamar a ferramenta de carregamento dinâmico
3. **Then** o sistema fará o parsing interno da estrutura e me devolverá apenas a string contida em `prompt`.

### User Story 3 - [Resiliência de Estado Sem Redis] (Priority: P2)
Como CLI do Kit Vitalia, quero poder ler o estado atual do orquestrador a partir de um arquivo JSON caso o container do Redis caia, para não interromper a esteira de CI/CD.

**Why this priority**: Permite dogfooding e acompanhamento autônomo sem dependência 100% estrita de containers externos (P2).

**Acceptance Scenarios**:
1. **Given** que o serviço do Redis está derrubado
2. **When** o orquestrador tenta atualizar o `sprint_state`
3. **Then** a requisição falha silenciosamente no Redis e um arquivo `.vitalia/pipeline.json` é gerado no disco com os dados de estado.

---

## 4. Glossário
| Termo | Definição |
|---|---|
| **TOML** | Formato de arquivo usado pelo Kit v0.4.0 para declarar metadados das extensões (`spec-plan.toml`). |
| **pipeline.json** | Arquivo de estado persistido em disco usado pelo Kit para rastrear a feature em andamento. |
