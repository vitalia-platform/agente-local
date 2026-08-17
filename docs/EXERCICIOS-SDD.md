# Mini-Curso: Exercícios Práticos de SDD (Katas)

Bem-vindo ao centro de treinamento do Vitalia Agente Local. Estes exercícios (katas) foram desenhados para reprogramar sua forma de interagir com Inteligências Artificiais em ambientes de engenharia. 

Recomendamos que você os faça na ordem estabelecida.

---

## 🟢 UNIDADE 1: Fundamentos (Iniciante)
**Pré-requisito:** Leitura do `ONBOARDING.md`.

O objetivo desta unidade é erradicar o "Vibe Coding" e aprender a guiar a IA mecanicamente através de especificações.

### Exercício 1: O "Hello World" Mecânico
**A Missão:** Construir uma calculadora de linha de comando simples.
1. Crie um arquivo chamado `calculadora-spec.md`.
2. Em vez de pedir ao agente "Crie uma calculadora para mim", escreva no arquivo as regras de negócio: O que ela soma? Como lida com divisão por zero?
3. Acione o fluxo mecânico: Peça ao agente (usando a skill `/vitalia-spec-plan` se disponível, ou chamando-o diretamente) para ler sua spec e propor um `plan.md`.
4. Uma vez que o plano esteja aprovado por você, ordene a quebra de tarefas (`tasks.md`) e, só então, permita a geração do código.
**O que você aprende:** O fluxo rígido de estado `Spec -> Plan -> Tasks -> Implement`.

### Exercício 2: A Refatoração de Tarefas Atômicas
**A Missão:** Desconstruir um pedido genérico.
1. Inicie um chat com o agente e dê o pior comando possível: *"Adicione um botão de upload de foto no meu app".*
2. Imediatamente acione a skill `/vitalia-clarify` ou exija: *"Antes de codar, me faça até 5 perguntas críticas sobre esse botão e gere um tasks.md detalhado"*.
3. Observe as perguntas que o agente levantará (ex: Onde salvar a imagem? Qual tamanho máximo? Como lidar com erros de rede?).
**O que você aprende:** Como usar a IA analítica (O Arquiteto) para proteger a IA geradora (O Engenheiro).

---

## 🟡 UNIDADE 2: Arquitetura e Engenharia (Intermediário)
**Pré-requisito:** Leitura da Seção 1 e 2 do `ARCHITECTURE.md`.

Nesta unidade, vamos focar em resiliência e padronização.

### Exercício 3: O Kata da "Constituição"
**A Missão:** Definir regras inquebráveis para a IA.
1. Crie um arquivo `AGENTS.md` (Constituição do Projeto) e insira regras técnicas estritas (ex: *"Nunca use classes em Python, use apenas namedtuples e pure functions. Toda função deve ter type hints."*).
2. Escreva uma `spec.md` para um validador de e-mails comum.
3. Peça para a IA implementar.
4. Acione a skill de revisão (ex: `/vitalia-review`). Avalie se a IA obedeceu fielmente à Constituição ou se "escorregou" para os padrões com os quais foi treinada.
**O que você aprende:** Como alinhar o modelo ao padrão corporativo, superando o viés inato do LLM.

### Exercício 4: "Delete e Refaça"
**A Missão:** Provar que o Código é descartável; a Spec é eterna.
1. Escreva uma `spec.md` para um "Conversor de CSV para JSON". Peça para a IA implementá-lo junto com os testes.
2. Note os erros que a IA cometeu na primeira tentativa.
3. Volte na `spec.md`, atualize o documento para cobrir as falhas que causaram os erros (ex: *"Trate vírgulas dentro das aspas duplas no CSV"*).
4. Apague todo o código gerado, mantendo **apenas** a spec atualizada.
5. Peça para a IA gerar novamente, agora a partir da spec blindada, e observe se ela passa nos testes de primeira.
**O que você aprende:** Technical debt é eliminado corrigindo a Especificação, não apenas o código final.

---

## 🔴 UNIDADE 3: Domínio e Segurança (Avançado)
**Pré-requisito:** Leitura da Seção 3 do `ARCHITECTURE.md`.

Nesta unidade, exercitaremos os mecanismos de proteção contra falhas e *Domain Gates* (Filtros de Domínio Clínico).

### Exercício 5: O "Hand-off Clínico" (Medical Gate Trigger)
**A Missão:** Forçar o sistema a rejeitar uma especificação médica mal redigida.
1. O Vitalia foca em saúde. Escreva uma `spec.md` descuidada para uma *"Calculadora de IMC Clínico"*, apenas dizendo a fórmula (Peso / Altura²).
2. Acione o Agente Arquiteto e invoque a skill `/vitalia-medical-gate`.
3. O agente **deve falhar e se recusar a codar**, devolvendo alertas clínicos críticos. Ele exigirá que você especifique o que fazer se o peso for "negativo", qual tabela de classificação médica usar (OMS?), e limites (*borders*) fisiologicamente aceitáveis.
4. Atualize a `spec.md` com uma seção `## Critérios de Aceite (Clínicos)` detalhada e passe pelo Gate novamente.
**O que você aprende:** A usar agentes não apenas como geradores rápidos de código, mas como Auditores de Qualidade implacáveis em domínios de alto risco.

---

## 🟣 UNIDADE 4: Observabilidade e Tolerância a Falhas (Especialista)
**Pré-requisito:** Leitura da Seção 2 do `ARCHITECTURE.md` (ADR-03 e ADR-04).

Nesta unidade, ensinaremos como monitorar os LLMs na "caixa de vidro", garantindo que eles não rodem desgovernados consumindo a infraestrutura e a sua conta de API.

### Exercício 6: O "Loop" e o Abort
**A Missão:** Forçar o Agente Arquiteto e o Agente Engenheiro a debaterem infinitamente.
1. Escreva uma `spec.md` descuidada e conflituosa. Diga: *"O arquiteto deve propor A, mas o Engenheiro deve recusar categoricamente A e propor B. O Arquiteto deve insistir em A infinitamente"*.
2. Acione a interface de Observabilidade Web via WebSockets no Dashboard (endpoint `/ws/events`).
3. Dispare a execução. Você verá no WebSocket, em tempo real e de forma criptografada pelo Redis, os agentes discutindo.
4. **O momento chave:** Espere eles atingirem o limite rígido de interações (10 mensagens). Observe o AutoGen injetar `TextMentionTermination` (geralmente gerando `__VITALIA_ABORT__`) e travando a execução para salvar sua máquina.
5. **O que você aprende:** Os LLMs não são perfeitos e vão entrar em repetição estocástica. A infraestrutura (o "corpo" do agente) precisa ter os limites físicos e o log assíncrono para você agir a tempo.
