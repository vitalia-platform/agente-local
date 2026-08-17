# tools.py | Atualizado em: 24-07-2026 (Refatorado para Kit v0.4.0)
import os
import ast
import json
import redis
import psycopg2
import requests
from datetime import datetime
from ddgs import DDGS
from dotenv import load_dotenv
from config_manager import config
try:
    from logger import logger
except ImportError:
    logger = None

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Credenciais lidas estritamente do .env (Zero Hardcoding)
DB_USER = os.getenv("POSTGRES_USER", "vitalia_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "secret")
DB_NAME = os.getenv("POSTGRES_DB", "vitalia_db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

OLLAMA_URL = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434")
DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@localhost:{DB_PORT}/{DB_NAME}"

def update_sprint_state(task: str, status: str) -> str:
    """Persiste o estado da sprint atual no Redis de forma atômica, com fallback para JSON."""
    try:
        r = redis.Redis.from_url(config.get_redis_url(), decode_responses=True)
        r.ping() # Valida a conexão
        state = {"task": task, "status": status}
        r.hset("vitalia:sprint_state", mapping=state)
        return "Sucesso: Estado da sprint sincronizado no Redis."
    except Exception as e:
        # Graceful fallback: salva em disco se Redis estiver fora
        try:
            pipeline_file = config.pipeline_file
            state = {"task": task, "status": status, "updated_at": str(datetime.now())}
            with open(pipeline_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            return "Aviso: Redis indisponível. Estado salvo no disco (pipeline.json)."
        except Exception as file_e:
            return f"Erro Crítico ao sincronizar estado: Redis ({e}) / Disco ({file_e})"

def load_dynamic_skill(skill_name: str) -> str:
    """Carrega uma skill dinâmica (TOML ou Markdown fallback) para o contexto do agente."""
    try:
        import tomllib
    except ImportError:
        tomllib = None

    possible_paths = [
        config.skills_dir / skill_name / "SKILL.toml",
        config.skills_dir / f"{skill_name}.toml",
        config.skills_dir / skill_name / "SKILL.md"
    ]
    
    skill_path = None
    for p in possible_paths:
        if p.exists():
            skill_path = p
            break
            
    if not skill_path:
        return f"Erro: Skill '{skill_name}' não encontrada em {config.skills_dir}."
        
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if skill_path.suffix == ".toml":
            if tomllib is None:
                return "Erro: 'tomllib' não disponível. Atualize para Python 3.11+ para ler Skills TOML."
            data = tomllib.loads(content)
            # Retorna estritamente o prompt, evitando poluição de contexto
            return data.get("prompt", "")
        else:
            return content
    except Exception as e:
        return f"Erro ao processar a skill {skill_name}: {str(e)}"

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
    if logger:
        logger.log_event("tool_call", "save_code_to_rag", {"status": "started", "filepath": filepath, "length": len(content)})
        
    try:
        chunks = chunk_code_ast(content)
        
        # 1. Salva no Hot Cache (Redis)
        try:
            r = redis.Redis.from_url(config.get_redis_url(), decode_responses=True)
            r.set(f"vitalia:hot_rag:{filepath}", content, ex=86400) # Expira em 24h
            if logger: logger.log_event("system_log", "save_code_to_rag.redis", {"status": "success", "action": "set_hot_cache"})
        except Exception as redis_e:
            if logger: logger.log_event("system_log", "save_code_to_rag.redis", {"status": "error", "error": str(redis_e)})
            return f"Erro na conexão com Redis: {str(redis_e)}"
        
        # 2. Salva no PostgreSQL (Cold Storage + Vector)
        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            if logger: logger.log_event("system_log", "save_code_to_rag.pg", {"status": "connected"})
        except Exception as pg_e:
            if logger: logger.log_event("system_log", "save_code_to_rag.pg", {"status": "error", "error": str(pg_e)})
            return f"Erro na conexão com PostgreSQL: {str(pg_e)}"
            
        base_ollama_url = OLLAMA_URL.replace("/v1", "")
        
        for idx, chunk in enumerate(chunks):
            try:
                res = requests.post(f"{base_ollama_url}/api/embeddings", json={
                    "model": "nomic-embed-text",
                    "prompt": chunk
                })
                res.raise_for_status()
                embedding = res.json().get("embedding")
            except Exception as ollama_e:
                if logger: logger.log_event("system_log", "save_code_to_rag.ollama", {"status": "error", "chunk_index": idx, "error": str(ollama_e)})
                conn.rollback()
                cur.close()
                conn.close()
                return f"Erro RAG Ollama: {str(ollama_e)}"
            
            metadata = json.dumps({"chunk_index": idx, "total_chunks": len(chunks)})
            
            cur.execute(
                "INSERT INTO code_vectors (filepath, content, metadata, embedding) VALUES (%s, %s, %s, %s)",
                (filepath, chunk, metadata, embedding)
            )
            
        conn.commit()
        cur.close()
        conn.close()
        
        msg = f"Sucesso: {filepath} indexado no RAG ({len(chunks)} chunks) e salvo na memória quente."
        if logger: logger.log_event("tool_call", "save_code_to_rag", {"status": "success", "filepath": filepath})
        return msg
    except Exception as e:
        if logger: logger.log_event("tool_call", "save_code_to_rag", {"status": "error", "error": str(e)})
        return f"Erro RAG genérico: {str(e)}"

def read_working_memory(filepath: str) -> str:
    """Ferramenta Pull: Lê o código-fonte inteiro mais recente armazenado na memória quente."""
    try:
        r = redis.Redis.from_url(config.get_redis_url(), decode_responses=True)
        content = r.get(f"vitalia:hot_rag:{filepath}")
        if content:
            return content
        return f"Arquivo '{filepath}' não encontrado na memória quente. Você já o salvou nesta sprint?"
    except Exception as e:
        return f"Erro ao acessar Memória de Trabalho: {str(e)}"

def query_audit_log(limit: int = 5) -> str:
    """Recupera os últimos N turnos de raciocínio da stream de eventos."""
    try:
        r = redis.Redis.from_url(config.get_redis_url(), decode_responses=True)
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
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if not results:
                return "Nenhum resultado encontrado."
                
            formatted_results = []
            for r in results:
                formatted_results.append(f"Título: {r.get('title')}\nLink: {r.get('href')}\nResumo: {r.get('body')}\n")
                
            return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Erro na busca web: {str(e)}"
