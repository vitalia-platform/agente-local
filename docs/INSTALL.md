# Vitalia Control Plane - Guia de Instalação e Testes

Este pacote contém os arquivos necessários para subir o backend (FastAPI), o Dashboard e a infraestrutura básica (Redis, PostgreSQL) em uma nova máquina.

## 1. Pré-requisitos

Certifique-se de ter instalados na sua máquina:
- **Docker** e **Docker Compose**
- **Python 3.10+**
- (Opcional) Ambiente virtual (`venv` ou `conda`)

## 2. Configuração Inicial (Ambiente)

1. Renomeie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edite o `.env` com as configurações da sua máquina. **Atenção a 3 pontos vitais:**
   - **Banco de Dados & RAG:** As credenciais `POSTGRES_USER` e `POSTGRES_PASSWORD` são usadas não só pelo Dashboard, mas pela gravação de embeddings do RAG.
   - **Criptografia de Telemetria:** A variável `DASHBOARD_SECRET_KEY` (ou `HMAC_MASTER_SECRET`) é usada como semente do *Fernet* para **criptografar** todo o tráfego de logs assíncronos (incluindo o stream via WebSocket). Nunca use a chave padrão em produção.
   - **Redis:** A variável `REDIS_PASSWORD` e `REDIS_PORT` governam a fila de eventos e a ponte de ferramentas (Tool Bridge).

## 3. Subindo a Infraestrutura Base (Redis & DB)

Inicie os containers em background executando:

```bash
docker-compose up -d
```

Verifique se os containers `vitalia_redis` e `vitalia_db` estão rodando com `docker ps`.

## 4. Instalando Dependências do Python

É recomendável criar um ambiente virtual antes de instalar as dependências:

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

Instale as bibliotecas necessárias para o backend:

```bash
pip install -r requirements.txt
```

## 5. Iniciando o Servidor (Backend + Frontend Integrado)

Com o Redis rodando e as bibliotecas instaladas, inicie o `telemetry_api.py`, que gerencia as rotas da API, WebSockets e **serve os arquivos estáticos do frontend**.

Navegue até a pasta `vitalia-core` e execute:

```bash
cd vitalia-core
python telemetry_api.py
```

> **Nota:** Se estiver rodando o sistema completo (incluindo o orquestrador LLM), consulte a documentação de arquitetura. O comando acima foca no Painel de Controle (Dashboard).

## 6. Acesso e Testes do Dashboard

O Dashboard já está embutido no backend. Abra o seu navegador e acesse:
👉 **http://localhost:8000/**

1. **Security Gate (Login):** Digite a senha definida em `DASHBOARD_SECRET_KEY` no seu `.env` (ex: `vitalia_admin`).
2. **Telemetry HUD:** Verifique se a flag está `LIVE` verde.
3. **Inventário & Fila:** Navegue pelas abas Nodes e Queues para explorar os dados trafegados pelo Redis.

---

## 🛠 Troubleshooting & Hard Reset

Se o seu ambiente ficou instável, pastas foram corrompidas, portas entraram em conflito ou se os workers do orquestrador travaram em loop infinito com bancos fantasmas, a melhor abordagem é **destruir tudo e recriar**. 

Siga os passos abaixo na ordem correta para garantir que não sobrem resquícios da instalação antiga.

### Passo 1: Desligar e Limpar os Containers Docker

Containers órfãos e volumes antigos são a principal causa de falhas silenciosas. Vamos derrubar tudo e destruir os dados do Redis/Postgres:

```bash
# Para a execução atual e apaga os volumes montados (Bancos de dados, Cache)
docker-compose down -v

# (Opcional) Confirme se sobrou algum container vitalia rodando
docker ps -a | grep vitalia
```

### Passo 2: Destruir o Ambiente Virtual Python

Dependências desatualizadas no `pip` podem gerar problemas. Exclua a pasta `.venv`:

```bash
# Em sistemas Unix/Linux/Mac
rm -rf .venv

# Em sistemas Windows (PowerShell)
Remove-Item -Recurse -Force .venv
```

### Passo 3: Limpar Cache e Arquivos Temporários

O Python cria pastas `__pycache__` e a telemetria pode deixar arquivos estáticos de shard em `/logs`. Limpe os resquícios do sistema:

```bash
# Limpa todas as pastas de cache do python recursivamente
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type d -name ".pytest_cache" -exec rm -r {} +

# Apaga os logs salvos em disco (fallback do Redis)
rm -rf logs/*
```

### Passo 4: Resetar o Arquivo .env (Opcional)

Se você mexeu no `.env` e não sabe mais quais eram os valores padrão, sobrescreva-o com o `.env.example`:

```bash
# Apaga o atual
rm .env
# Recria a partir do template
cp .env.example .env
```
*(Lembre-se de reconfigurar suas senhas caso faça este passo).*

### Passo 5: Recriar o Ambiente

Agora o repositório está limpo como se tivesse acabado de ser clonado. Refaça a Instalação Rápida:

1. `docker-compose up -d`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`

---

## 9. Próximos Passos

A infraestrutura está montada! O ambiente Docker (PostgreSQL e Redis) está ativo, o backend Python está instanciado e as suas senhas do `.env` foram asseguradas.

👉 **Seu próximo passo obrigatório é voltar ao [ONBOARDING.md](./ONBOARDING.md#2-a-filosofia-sdd-o-fim-do-vibe-coding)** para dominar a teoria de Spec-Driven Development, a "Caixa de Vidro" (Dashboard) e o fluxo do nosso Orquestrador.

*(Para rodar testes de robustez na sua nova infraestrutura, acesse o [TESTING.md](./TESTING.md)).*
