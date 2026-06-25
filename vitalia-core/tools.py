# <!-- tools.py | Atualizado em: 24-06-2026 17:10:00(GMT-04:00) -->
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
import ast
import json
import redis
import psycopg2
import requests
from duckduckgo_search import DDGS

# Credenciais lidas estritamente do .env (Zero Hardcoding)
DB_USER = os.getenv("POSTGRES_USER", "vitalia_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "secret")
DB_NAME = os.getenv("POSTGRES_DB", "vitalia_db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
REDIS_PASS = os.getenv("REDIS_PASSWORD", "secret")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

OLLAMA_URL = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434")
DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@localhost:{DB_PORT}/{DB_NAME}"
REDIS_URL = f"redis://:{REDIS_PASS}@localhost:{REDIS_PORT}/0"

def update_sprint_state(task: str, status: str) -> str:
    """Persiste o estado da sprint atual no Redis de forma atômica."""
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        state = {"task": task, "status": status}
        r.hset("vitalia:sprint_state", mapping=state)
        return "Sucesso: Estado da sprint sincronizado no Redis."
    except Exception as e:
        return f"Erro ao sincronizar com Redis: {str(e)}"

def chunk_code_ast(content: str) -> list:
    """Usa o módulo nativo ast para separar classes/funções inteiras."""
    chunks = []
    try:
        tree = ast.parse(content)
        lines = content.split('\n')
        last_end = 0
        
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = node.end_lineno
                
                # Texto antes do nó (imports, variáveis globais, etc)
                if start > last_end:
                    chunk = '\n'.join(lines[last_end:start]).strip()
                    if chunk:
                        chunks.append(chunk)
                
                # O nó (função ou classe) inteiro preservado
                chunks.append('\n'.join(lines[start:end]))
                last_end = end
                
        # Remanescente
        if last_end < len(lines):
            chunk = '\n'.join(lines[last_end:]).strip()
            if chunk:
                chunks.append(chunk)
                
    except SyntaxError:
        # Fallback para chunking bruto se não for Python válido
        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
        
    return chunks if chunks else [content]

def save_code_to_rag(filepath: str, content: str) -> str:
    """Faz o chunking AST do código, salva temporariamente no Redis (Hot) e gera embeddings no pgvector."""
    try:
        chunks = chunk_code_ast(content)
        
        # 1. Salva no Hot Cache (Redis)
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        r.set(f"vitalia:hot_rag:{filepath}", content, ex=86400) # Expira em 24h
        
        # 2. Salva no PostgreSQL (Cold Storage + Vector)
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        for idx, chunk in enumerate(chunks):
            res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
                "model": "nomic-embed-text",
                "prompt": chunk
            })
            res.raise_for_status()
            embedding = res.json().get("embedding")
            
            metadata = json.dumps({"chunk_index": idx, "total_chunks": len(chunks)})
            
            cur.execute(
                "INSERT INTO code_vectors (filepath, content, metadata, embedding) VALUES (%s, %s, %s, %s)",
                (filepath, chunk, metadata, embedding)
            )
            
        conn.commit()
        cur.close()
        conn.close()
        return f"Sucesso: {filepath} indexado no RAG ({len(chunks)} chunks) e salvo na memória quente."
    except Exception as e:
        return f"Erro RAG: {str(e)}"

def read_working_memory(filepath: str) -> str:
    """Ferramenta Pull: Lê o código-fonte inteiro mais recente armazenado na memória quente."""
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        content = r.get(f"vitalia:hot_rag:{filepath}")
        if content:
            return content
        return f"Arquivo '{filepath}' não encontrado na memória quente. Você já o salvou nesta sprint?"
    except Exception as e:
        return f"Erro ao acessar Memória de Trabalho: {str(e)}"

def query_audit_log(limit: int = 5) -> str:
    """Recupera os últimos N turnos de raciocínio da stream de eventos."""
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        # XREVRANGE lê a stream de trás para frente (+ para -) limitando
        events = r.xrevrange("vitalia:events", "+", "-", count=limit)
        if not events:
            return "Nenhum histórico recente encontrado."
        
        history = []
        for event_id, event_data in events:
            if event_data.get("type") == "llm_turn":
                try:
                    payload = json.loads(event_data.get("payload", "{}"))
                    history.append(f"Turno [{event_data.get('timestamp')}] - {event_data.get('source')}:\n{payload.get('reasoning', 'Sem raciocínio')}")
                except:
                    pass
        return "\n\n".join(history)
    except Exception as e:
        return f"Erro ao acessar auditoria: {str(e)}"

def web_search(query: str) -> str:
    """Busca informações na web usando DuckDuckGo."""
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=3)
        if not results:
            return "Nenhum resultado encontrado."
            
        formatted_results = []
        for r in results:
            formatted_results.append(f"Título: {r.get('title')}\nLink: {r.get('href')}\nResumo: {r.get('body')}\n")
            
        return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Erro na busca web: {str(e)}"
