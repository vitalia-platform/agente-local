# Vitalia Agente Local — Arquitetura e Engenharia (Módulos 2 e 3)

> **Foco do Módulo:** Tomada de decisão, regras globais, resiliência de software e Gates de Domínio Críticos. Assumimos que você já domina os conceitos básicos (Onboarding).

Este manual destina-se a colaboradores com domínio avançado de Python/asyncio, Docker, Redis e comportamento de LLMs. Aqui registramos *por que* tomamos certas decisões arquiteturais e como elas suportam nosso workflow de Spec-Driven Development (SDD).

---

## 1. Topologia de Hardware e Orquestração Híbrida

Modelos de linguagem eficientes exigem VRAM (Memória de Vídeo). Como desenvolvedores muitas vezes não têm placas de vídeo corporativas em seus notebooks locais, adotamos uma **arquitetura híbrida**.

### 1.1 Dois Nós, Um Sistema
- **Nó 1 (Notebook do Desenvolvedor):** Processador em CPU ou GPU fraca. Roda o motor central (Redis, Banco RAG, API). O Agente Arquiteto vive aqui, alimentado por modelos leves e inteligentes (ex: `llama3.2:3b`).
- **Nó 2 (Servidor Local/Cloud):** Máquina com GPU dedicada (ex: GTX 1060). O Agente Engenheiro vive aqui, focando apenas em codar rápido através de LLMs grandes (ex: `qwen2.5-coder:7b`).

### 1.2 Configuration via `.env`
O sistema é inteiramente adaptável através do `.env`. Você não reescreve código se trocar de hardware:
- `NO1_TOOL_CALLING_NATIVE=false`: Se ativado, aciona o Tool Bridge via Redis para compensar a deficiência do LLM rodando em CPU no Nó 1.
- `NO2_TOOL_CALLING_NATIVE=true`: O Nó 2 entende JSON estruturado da API nativa de ferramentas.

---

## 2. Decisões de Design (ADRs)

### ADR-01 — Tool Bridge Assíncrono via Redis Streams
**O Problema:** O framework AutoGen roteia a resposta do LLM *antes* de injetar o resultado de uma ferramenta.
**A Decisão:** Criamos o wrapper `VitaliaOllamaClient` que escuta e trava a resposta na thread usando `asyncio.Event`. Ele posta na stream `vitalia:tool_requests`, o worker executa, posta em `vitalia:tool_results`, e o wrapper entrega o bloco mastigado ao AutoGen.
**Trade-off:** Um overhead mínimo de latência (~1ms no Redis) em troca de estabilidade massiva no loop AutoGen.

### ADR-02 — Contexto Descentralizado (Dual-Git)
A memória do agente sobre o projeto **não vive no código fonte principal**.
**A Decisão:** Mantemos um repositório Git oculto ou secundário (ex: `*-contexto`) onde salvamos o histórico de conversões, `spec.md` aprovadas e resumos do RAG.
**Por quê?** Se múltiplos desenvolvedores e agentes estiverem colaborando, o código principal fica limpo (sem *diffs* de agentes quebrados), e o contexto é fundido periodicamente pela skill `/vitalia-session-consolidate`.

### ADR-03 — Observabilidade em Tempo Real via WebSockets
**O Problema:** Durante a execução assíncrona, é difícil acompanhar as razões de tomada de decisão (stdout) do agente.
**A Decisão:** Todos os eventos da execução são criptografados (usando `Fernet` via a chave `DASHBOARD_SECRET_KEY`) e postados numa fila do Redis chamada `vitalia_events`. A API (FastAPI) consome essa fila em `/ws/events` e os despacha para a interface web via WebSockets.
**Trade-off:** A latência adicional de criptografia para cada log é mitigada pelo desacoplamento via fila, permitindo telemetria sem bloquear a inferência do LLM.

### ADR-04 — Mecanismo Anti-Loop e Termination
**O Problema:** Agentes soltos frequentemente entram em repetição estocástica (debates cíclicos entre si).
**A Decisão:** Aproveitamos o controle nativo do AutoGen utilizando a combinação estrutural de `MaxMessageTermination(max_messages=10)` junto ao aborto forçado `TextMentionTermination("__VITALIA_ABORT__")`.
**Trade-off:** Não há complexidade adicional de verificação de loops com *heurísticas*, mas podemos causar falsos positivos em tarefas complexas que exijam mais de 10 interações, forçando-as a abortarem por segurança.

### ADR-05 — RAG Context Management
**O Problema:** Modelos em hardware modesto lidam mal com contextos gigantescos.
**A Decisão:** Criamos uma arquitetura dual: A gravação simultânea em **Hot Cache** (`vitalia:hot_rag:*` no Redis) para leituras relâmpago de memória curta na mesma *sprint*, e gravação em **Cold Vector Storage** (PostgreSQL com pgvector + `nomic-embed-text`) para pesquisa semântica pesada.

---

## 3. Segurança e Domínio Restrito (Módulo 3)

No SDD, a arquitetura deve barrar alucinações perigosas *antes* que virem código. O Vitalia integra **Gates de Domínio**.

### 3.1 O "Medical Gate"
Muitos sistemas do Vitalia atuam no domínio da Saúde. A IA é estritamente proibida de tomar decisões clínicas.
Quando o Agente Arquiteto lê uma `spec.md`, ele valida seu escopo contra o Medical Gate (skill `vitalia-medical-gate`). Se a especificação lidar com calculos fisiológicos (ex: dosagem, IMC, triagem), a skill força o desenvolvedor a escrever explicitly na Spec:
- Quais são os limites (*borders*) da função?
- Qual a referência científica oficial (protocolo médico)?
- Como tratar os *outliers*?

Sem a presença de uma seção `## Critérios de Aceite (Clínicos)` na Spec, o Agente Engenheiro recebe um **TERMINATE** automático e não gera nenhum código.

---

## 📚 Próximos Passos

Pronto para dominar as técnicas de Arquitetura e Engenharia? 

Vá para **[EXERCICIOS-SDD.md](./EXERCICIOS-SDD.md)** e complete a **Unidade 2** (para treinar resiliência de código e as Leis do Projeto) e a **Unidade 3** (para disparar os Gates de Domínio Clínico).
