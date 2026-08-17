# Vitalia Agente Local

Bem-vindo ao **Agente Local** da plataforma Vitalia. Este repositório contém a infraestrutura e os workflows que habilitam o desenvolvimento de software guiado por inteligência artificial, garantindo que todo código e configuração sigam regras estritas de arquitetura e qualidade clínica.

## A Abordagem Vitalia

O ecossistema Vitalia se diferencia pelo rigor estrutural na orquestração de Agentes IA (via AutoGen):

1. **Spec-Driven Development (SDD):** A especificação (`spec.md`) é a Fonte da Verdade absoluta. Nenhuma linha de lógica é escrita sem que uma spec tenha sido redigida e validada por humanos e agentes arquitetos.
2. **Medical Gate:** Gateways de domínio garantem checagens de segurança clínica restritas antes da geração de código voltado para o setor de saúde.
3. **Contexto Descentralizado (Dual-Git):** A memória da IA (specs e histórico RAG) é armazenada de forma isolada, protegendo o código de negócio contra regressões causadas por alucinações.

---

## 📖 Mini-Curso e Documentação (Índice)

Preparamos uma documentação estruturada em formato de "Mini-Curso" para que você entenda não apenas a infraestrutura (como rodar), mas também a mecânica de trabalho (como operar a IA de forma segura).

Siga os módulos na ordem abaixo:

- **[Módulo 1: Onboarding e Fundamentos SDD](./docs/ONBOARDING.md)**
  *Como configurar seu ambiente (Docker, `.env`) e sair da armadilha do "Vibe Coding".*

- **[Módulo 2 e 3: Arquitetura e Engenharia Avançada](./docs/ARCHITECTURE.md)**
  *Decisões de Design (ADRs), topologia de hardware (Tool Bridge em GPU vs CPU) e Medical Gates.*

- **[Exercícios Práticos (Katas)](./docs/EXERCICIOS-SDD.md)**
  *Exercícios práticos de "Hello World" a Hand-offs Clínicos para treinar sua interação com a IA.*

- **[Pipeline de Teste E2E (TESTING.md)](./docs/TESTING.md)**
  *O guia fonte-da-verdade para testes de infraestrutura na sua máquina.*

---

## ⚙️ Instalação Rápida (Kit Global)

Para inicializar a mecânica SDD no seu ambiente, baixe o **Kit de Agentes Global** e ative-o neste projeto:

```bash
# 1. Instalação Global do Kit Vitalia
wget -qO- https://raw.githubusercontent.com/vitalia-platform/agente-local-spec-kit/main/scripts/bootstrap.sh | bash

# 2. Ativação no Projeto Local
git clone git@github.com:vitalia-platform/agente-local.git
cd agente-local
bash ~/.vitalia-spec/scripts/install.sh
```

> **Aviso:** Antes da instalação, crie um repositório vazio no GitHub que servirá de **repositório de contexto** (ex: `revisao-[tema]-contexto`). O script pedirá a URL SSH dele.
> 
> 🔗 **Para problemas, instruções manuais e Hard Reset:** Consulte o guia [Instalação e Troubleshooting](./docs/INSTALL.md).
> 🔗 **Para validação de hardware (GPU/Rede):** Consulte o guia [Bench Test](./docs/BENCH_TEST.md).

## 📝 Histórico e Evolução

Consulte nosso **[CHANGELOG.md](./CHANGELOG.md)** para acompanhar o estado atual, features implementadas e a evolução da arquitetura do projeto.
