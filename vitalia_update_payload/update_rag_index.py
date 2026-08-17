import os
import hashlib
import psycopg2
from typing import List, Dict

# Conexão com o banco pgvector (exemplo)
DB_DSN = os.environ.get("PGVECTOR_DSN", "postgresql://vitalia:vitalia@localhost:5432/vitalia_rag")

def get_file_hash(filepath: str) -> str:
    """Gera um hash SHA-256 do conteúdo do arquivo para controle de stale data."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def sync_rag_index(directory_to_scan: str):
    """
    Realiza o sync da pasta com o banco pgvector.
    Insere/Atualiza apenas se o content_hash mudou.
    Remove vetores órfãos (Janitor cleanup).
    """
    active_files = {}
    
    # 1. Mapeia os arquivos locais atuais
    for root, _, files in os.walk(directory_to_scan):
        for file in files:
            if file.endswith(('.md', '.json', '.yml', '.yaml', '.env')):
                filepath = os.path.join(root, file)
                active_files[filepath] = get_file_hash(filepath)

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    try:
        # 2. Busca o estado atual no banco
        cur.execute("SELECT filepath, content_hash FROM document_embeddings")
        db_files = {row[0]: row[1] for row in cur.fetchall()}

        # 3. Identifica Novos e Modificados
        for filepath, current_hash in active_files.items():
            if filepath not in db_files or db_files[filepath] != current_hash:
                print(f"[RAG SYNC] Inserindo/Atualizando: {filepath}")
                # Aqui o sistema chamaria a API de embedding (ex: text-embedding-3) e faria o UPSERT
                # cur.execute("INSERT INTO document_embeddings ... ON CONFLICT DO UPDATE")

        # 4. Janitor Cleanup: Remove arquivos que não existem mais localmente
        for db_filepath in db_files.keys():
            if db_filepath not in active_files:
                print(f"[RAG JANITOR] Removendo stale document: {db_filepath}")
                cur.execute("DELETE FROM document_embeddings WHERE filepath = %s", (db_filepath,))
        
        conn.commit()
        print("[RAG] Sincronização e Limpeza concluídas com sucesso.")

    except Exception as e:
        conn.rollback()
        print(f"[RAG ERROR] Falha na sincronização: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Quando rodado via `hooks.after` do session-end, varre o ambiente e as specs
    sync_rag_index("./docs")
    sync_rag_index("./specs")
