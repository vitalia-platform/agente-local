# Vitalia Agente Local — Manual de Onboarding (Módulo 1)

> **Foco do Módulo:** Sair do "Vibe Coding" e entender a mecânica do SDD (Spec-Driven Development), o Orquestrador Híbrido Vitalia, o Dashboard e a Memória 3-Tier.

Bem-vindo(a) ao projeto! Este documento vai prepará-lo(a) teórica e tecnicamente para trabalhar no Agente Local, a fundação de nossa automação com inteligência artificial.

---

## 1. Pré-requisitos e Instalação

** PARE AQUI! **

Para garantir que sempre haja uma **Única Fonte da Verdade (Single Source of Truth)** no nosso projeto, as instruções de instalação (Docker, Python, Ollama, `.env`) foram movidas estritamente para o arquivo de infraestrutura.

👉 **Vá para o [INSTALL.md](./INSTALL.md)**, siga todos os passos para subir o sistema e, quando o seu backend e Dashboard estiverem rodando, volte para cá para continuarmos a teoria.

*(Para testes automatizados e validações completas End-to-End da instalação, consulte o [TESTING.md](./TESTING.md) e a bateria do [BENCH_TEST.md](./BENCH_TEST.md)).*

---

## 2. A Filosofia SDD: O Fim do "Vibe Coding"

### O que é "Vibe Coding"?
É a prática comum de pedir algo vago a um LLM ("Crie um botão azul que salva no banco") e torcer para o resultado ser bom. Quando o sistema cresce, o "vibe coding" falha catastroficamente: o agente esquece o contexto, reescreve arquivos desnecessários e introduz bugs silenciosos.

### O que é Spec-Driven Development (SDD)?
SDD trata o LLM como um **compilador humano**.
- **A Especificação (`spec.md`) é a Fonte da Verdade:** Nenhuma linha de código é gerada sem uma spec. Se o código não condiz com a spec, o código está errado, mesmo que "funcione".
- **Fluxo Socrático:** Quando um humano tenta pular etapas, o agente faz perguntas (Socratic Protocol) para identificar *blind spots* na arquitetura.
- **Micro-passos (`tasks.md`):** A implementação é quebrada em fases verificáveis. O agente marca `[x]` para cada fase concluída.

---

## 3. Conceitos do Orquestrador

O Vitalia não é um simples chatbot. É um **Orquestrador Híbrido** construído sobre o AutoGen da Microsoft, conectando múltiplos agentes.

### 3.1. AutoGen e os Papéis
No Vitalia, o LLM adota duas "personas" que conversam entre si:
- **Arquiteto (Nó 1 - CPU):** Pensa, pesquisa na web (`web_search`), refina a especificação. Geralmente roda um modelo menor (ex: `llama3.2:3b`).
- **Engenheiro (Nó 2 - GPU):** Especialista em sintaxe (ex: `qwen2.5-coder`). Recebe os comandos do arquiteto, escreve o código, testa e salva os resultados no banco de RAG.

### 3.2. A Solução: Tool Bridge (Redis Streams)
Modelos pequenos rodando em CPU frequentemente sofrem com alucinações na hora de chamar ferramentas. Para corrigir isso, o Vitalia implementa um "Tool Bridge" revolucionário:
1. O LLM retorna um JSON cru.
2. O **VitaliaOllamaClient** intercepta a resposta *antes* dela chegar ao AutoGen.
3. O wrapper posta a intenção na fila (`Redis Streams`).
4. Um worker isolado pega o pedido, executa e posta o resultado, que é devolvido ao AutoGen de forma segura.

---

## 4. A Caixa de Vidro: O Dashboard de Observabilidade

Trabalhar com orquestradores Multi-Agentes no terminal pode ser frustrante, pois a IA "pensa" de forma assíncrona.

Para acelerar drasticamente o seu aprendizado em SDD, criamos um **Dashboard Visual em tempo real**. Todo o stdout (saída) dos agentes é roteado para a web usando WebSockets (veja os detalhes técnicos no [ARCHITECTURE.md - ADR-03](./ARCHITECTURE.md)).

### Vantagens para o Aprendizado
- **Raciocínio Exposto:** Você verá o *prompt* interno que os agentes trocam entre si. Se a IA cometer um erro, você saberá exatamente se foi porque o Arquiteto especificou mal, ou se o Engenheiro desobedeceu.
- **Mecanismo Anti-Loop (Resiliência):** Às vezes, LLMs entram em repetição estocástica (um *loop* de teimosia). Se isso acontecer, o Dashboard mostrará, após o limite de 10 mensagens, o orquestrador injetar a diretiva `__VITALIA_ABORT__` para travar a execução e proteger a infraestrutura (veja [ARCHITECTURE.md - ADR-04](./ARCHITECTURE.md)).

---

## 5. Memória 3-Tier: RAG, Contexto e Hot Cache

No Vitalia, a memória da IA sobre o projeto **não vive no código fonte principal** ([ARCHITECTURE.md - ADR-02](./ARCHITECTURE.md)), e os agentes sofrem de amnésia a cada nova execução. Para conectá-los ao contexto, usamos uma estrutura de 3 camadas:

### 5.1 O Hot Cache (Redis)
Quando o agente cria um código na *sprint* atual, ele o salva instantaneamente no Redis (`vitalia:hot_rag:*`). Isso garante que, no turno seguinte, ele lembre exatamente do que acabou de escrever em milissegundos.

### 5.2 O Cold Storage Vector (PostgreSQL)
Em background, tudo o que vai para o Hot Cache é vetorizado via `nomic-embed-text` e gravado permanentemente no banco relacional para pesquisa semântica futura.

### 5.3 O Repositório de Contexto (Git Separado)
Decisões arquiteturais de alto nível e logs de sessões passadas são fundidos num sub-repositório `.vitalia/memory`. 

Essa separação garante performance imediata e preserva os tokens da janela de contexto para quando realmente precisarem raciocinar (veja [ARCHITECTURE.md - ADR-05](./ARCHITECTURE.md) para mais aprofundamento técnico).

---

## 📚 Próximos Passos

Agora que você compreende a teoria fundamental, o Orquestrador, o Dashboard e a Memória 3-Tier, é hora de colocar a mão na massa!

Vá para **[EXERCICIOS-SDD.md](./EXERCICIOS-SDD.md)** e complete a **Unidade 1** para fixar a mecânica de criação de Specs e quebra de tarefas.

> *Para decisões arquiteturais avançadas e configurações detalhadas, consulte o [ARCHITECTURE.md](./ARCHITECTURE.md).*
