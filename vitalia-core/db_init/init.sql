-- Ativa a extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Cria a tabela de vetores de código
CREATE TABLE IF NOT EXISTS code_vectors (
    id SERIAL PRIMARY KEY,
    filepath TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(768) -- nomic-embed-text usa 768 dimensões
);
