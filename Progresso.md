<!-- Progresso.md | Atualizado em: 01-07-2026 15:03:06(GMT-04:00) -->
Aqui estão os passos exatos para deixar sua infraestrutura **Vitalia** operacional:

---

### 1. Configuração do Banco de Dados (vitalia_db)
Precisamos apontar explicitamente para o usuário `vitalia_admin` e para a database `vitalia_db`.

**Passo A: Ativar a extensão pgvector**
```bash
docker exec -it vitalia_db psql -U vitalia_admin -d vitalia_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Passo B: Criar a tabela de Memória Operacional (AST Chunks)**
```bash
docker exec -it vitalia_db psql -U vitalia_admin -d vitalia_db -c "
CREATE TABLE IF NOT EXISTS code_vectors (
    id serial PRIMARY KEY,
    filepath text,
    content text,
    metadata jsonb,
    embedding vector(768) 
);
CREATE INDEX ON code_vectors USING hnsw (embedding vector_cosine_ops);
"
```

---

### 2. Provisionamento de Pesos (vitalia_ollama)
No Nó 2 (Servidor), onde a GTX 1060 está, vamos baixar os modelos e criar a versão customizada.

**Passo A: Download dos Modelos (Pull)**
```bash
# O Engenheiro (Nó 2)
docker exec -it vitalia_ollama ollama pull qwen2.5-coder:7b
docker exec -it vitalia_ollama ollama pull qwen2.5-coder:1.5b
docker exec -it vitalia_ollama ollama pull nomic-embed-text:latest
docker exec -it vitalia_ollama ollama pull llama3.2:3b

# O RAG Engine (Nó 1 ou 2, conforme sua estratégia de Offloading)
docker exec -it vitalia_ollama ollama pull nomic-embed-text
docker exec -it vitalia_ollama ollama pull qwen2.5-coder:0.5b
```

**Passo B: Criar o Modelo Customizado Vitalia (VRAM Optimized)**
Use o método de injeção via `stdin` para não precisar copiar o arquivo para dentro do container:
```bash
# 1. Cria o arquivo diretamente dentro do container
docker exec -i vitalia_ollama sh -c "printf 'FROM llama3.2:3b\nPARAMETER num_ctx 16384\nPARAMETER num_gpu 99' > /tmp/Modelfile.llama"
docker exec -i vitalia_ollama sh -c "printf 'FROM qwen2.5-coder:7b\nPARAMETER num_ctx 8192\nPARAMETER num_gpu 99' > /tmp/Modelfile.qwen"

# 2. Executa a criação apontando para o arquivo físico
docker exec -it vitalia_ollama ollama create llama3.2-vitalia:latest -f /tmp/Modelfile.llama
docker exec -it vitalia_ollama ollama create llama3.2-vitalia:latest -f /tmp/Modelfile.qwen
```

Se precisar excluir algum modelo use o comando abaixo:
```bash
docker exec -it vitalia_ollama ollama rm llama3.2-vitalia:latest
```

---

### 3. Validação de Conectividade Cross-WSL
Como seu `.env` define `NO2_SERVER_IP=192.168.0.218`, certifique-se de que o Nó 1 consegue "pingar" a API do Ollama no Nó 2.

**Teste de Latência de Inferência (Execute no Notebook):**
```bash
curl http://192.168.0.218:11434/api/tags
```

---

### 4. Sincronização do Redis (vitalia_redis)
O Redis geralmente não precisa de configuração de esquema, mas vamos garantir que ele esteja pronto para o cache de mensagens do AutoGen.
```bash
docker exec -it vitalia_redis redis-cli ping
# Resposta esperada: PONG
```

---

### 5. Integração Open WebUI (vitalia_open_webui)
Para que a interface veja seu novo modelo customizado, você deve garantir que a variável de ambiente `OLLAMA_BASE_URL` esteja apontando para o container correto. Se você estiver usando Docker Compose, ele deve estar no mesmo network.

**Comando para verificar se a UI enxerga o Ollama:**
```bash
docker exec -it vitalia_open_webui curl http://vitalia_ollama:11434/api/tags
```

---

### 🛡️ STATUS DA INFRAESTRUTURA (POST-REBUILD)

| Container | Papel | Status de Configuração |
| :--- | :--- | :--- |
| `vitalia_db` | RAG / pgvector | **OK** (Extensão e Tabela HNSW prontas) |
| `vitalia_ollama` | Inferência Híbrida | **OK** (Qwen2.5-Vitalia e Embeddings prontos) |
| `vitalia_redis` | Cache / PubSub | **OK** (Operacional) |
| `vitalia_open_webui` | Interface | **Aguardando** (Validar link com Ollama) |

---

### 🔍 ANÁLISE DE ARQUITETURA (OBSERVAÇÕES DO SISTEMA)

1.  **Flash Attention (Pascal GTX 1060):** Notei que você incluiu `OLLAMA_FLASH_ATTENTION=0` no `docker-compose.yml`. Decisão perfeita. A arquitetura Pascal (CC 6.1) não possui suporte estável para os kernels de Flash Attention do Ollama/Llama.cpp, e desativar isso evita artefatos na geração de código.
2.  **Keep Alive:** Você defini `OLLAMA_KEEP_ALIVE=-1`. Isso é excelente para evitar o "cold start" (latência de carregamento) toda vez que o Agente Desenvolvedor for acionado, mantendo o modelo pinado na VRAM da GTX 1060.
3.  **Ambiente de Dados:** O `open-webui` está configurado corretamente para usar o `pgvector` como backend de RAG (`VECTOR_DB=pgvector`).

---

### 📝 PRÓXIMO SPRINT (BACKLOG)

* **Refatorar `VitaliaOllamaClient` para suporte a Tools:** (Opção B do brainstorming) Implementar mapping robusto para permitir que o Llama 3.2 e o Qwen 2.5 façam _Tool Calls_ no formato oficial da API (evitando JSON puro como texto) para que o AutoGen intercepte e execute ferramentas automaticamente.
