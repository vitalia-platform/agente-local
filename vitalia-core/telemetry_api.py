# telemetry_api.py | Atualizado em: 26-06-2026
import os
import json
import asyncio
import docker
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import dotenv
import redis.asyncio as redis_async
import redis as redis_sync
import subprocess
import httpx

try:
    from logger import logger
except ImportError:
    # Caso seja executado de um contexto sem o logger
    logger = None

env_path = os.path.join(os.path.dirname(__file__), '../.env')
dotenv.load_dotenv(env_path)

SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

REDIS_PASS = os.getenv("REDIS_PASSWORD", "secret")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://:{REDIS_PASS}@localhost:{REDIS_PORT}/0"

app = FastAPI(title="Vitalia Control Plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Aviso: Não foi possível conectar ao Docker Socket: {e}")
    docker_client = None


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/api/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.password != SECRET_KEY:
        raise HTTPException(status_code=400, detail="Senha mestra incorreta")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    r = redis_async.Redis.from_url(REDIS_URL, decode_responses=True)
    stream_name = "vitalia_events"
    last_id = '$'
    
    try:
        while True:
            events = await r.xread({stream_name: last_id}, count=10, block=1000)
            if events:
                for stream, messages in events:
                    for msg_id, msg_data in messages:
                        last_id = msg_id
                        await websocket.send_json(msg_data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        await r.aclose()


class ControlRequest(BaseModel):
    container_name: str

@app.post("/api/control/restart")
async def restart_container(req: ControlRequest, username: str = Depends(get_current_user)):
    if not docker_client:
        raise HTTPException(status_code=500, detail="Docker integration unavailable")
    try:
        container = docker_client.containers.get(req.container_name)
        container.restart()
        return {"status": "success", "message": f"Container {req.container_name} restarted"}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gpu-status")
def get_gpu_status():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.free,memory.used", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return {"error": "nvidia-smi falhou"}
            
        lines = result.stdout.strip().split('\n')
        gpus = []
        for idx, line in enumerate(lines):
            parts = line.split(',')
            if len(parts) >= 3:
                gpus.append({
                    "gpu_index": idx,
                    "total_mb": int(parts[0].strip()),
                    "free_mb": int(parts[1].strip()),
                    "used_mb": int(parts[2].strip()),
                })
        return {"gpus": gpus}
    except Exception:
        return {"error": "Sem GPU local"}

# --------- SETTINGS & BENCHMARK ---------

class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

@app.get("/api/settings")
async def get_settings(username: str = Depends(get_current_user)):
    keys = ["VITALIA_PUBSUB_ENABLED", "NO1_LOCAL_OLLAMA_URL", "NO2_SERVER_IP", "ROUTER_LLM_PROFILE"]
    return {k: os.getenv(k, "") for k in keys}

@app.post("/api/settings")
async def update_settings(req: SettingsUpdate, username: str = Depends(get_current_user)):
    try:
        for k, v in req.settings.items():
            dotenv.set_key(env_path, k, v)
            os.environ[k] = v
        return {"status": "success", "message": "Settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/llms")
async def list_llms(username: str = Depends(get_current_user)):
    url1 = os.getenv("NO1_LOCAL_OLLAMA_URL", "http://localhost:11434/v1").replace("/v1", "/api/tags")
    url2 = os.getenv("NO2_SERVER_IP", "").replace("/v1", "/api/tags")
    
    results = {"node1": [], "node2": []}
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r1 = await client.get(url1)
            if r1.status_code == 200:
                results["node1"] = r1.json().get("models", [])
        except:
            pass
        if url2:
            try:
                r2 = await client.get(url2)
                if r2.status_code == 200:
                    results["node2"] = r2.json().get("models", [])
            except:
                pass
    return results

class BenchmarkRequest(BaseModel):
    endpoint_url: str  # e.g., http://localhost:11434/api/generate
    model_name: str

@app.post("/api/benchmark")
async def run_benchmark(req: BenchmarkRequest, username: str = Depends(get_current_user)):
    url = req.endpoint_url
    if not url.endswith("/api/generate"):
        url = url.replace("/v1", "") + "/api/generate"
        
    payload = {
        "model": req.model_name,
        "prompt": "Hello",
        "stream": False
    }
    
    if logger:
        logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_start", "url": url, "model": req.model_name})
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Warm-up
            if logger: logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_warmup", "model": req.model_name})
            warm_resp = await client.post(url, json=payload)
            warm_resp.raise_for_status()
            warm_data = warm_resp.json()
            load_duration_ms = warm_data.get("load_duration", 0) / 1e6
            
            # 2. Inference Run
            if logger: logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_inference", "model": req.model_name})
            inf_resp = await client.post(url, json=payload)
            inf_resp.raise_for_status()
            inf_data = inf_resp.json()
            
            eval_count = inf_data.get("eval_count", 0)
            eval_duration_ns = inf_data.get("eval_duration", 1) # prevent div/0
            tokens_per_sec = (eval_count / eval_duration_ns) * 1e9 if eval_duration_ns > 0 else 0
            
            if logger:
                logger.log_event("system_log", "TelemetryAPI", {
                    "event": "benchmark_success", 
                    "model": req.model_name, 
                    "load_ms": load_duration_ms, 
                    "tps": tokens_per_sec
                })
            
            return {
                "status": "success",
                "load_duration_ms": load_duration_ms,
                "tokens_per_sec": tokens_per_sec,
                "model": req.model_name
            }
            
        except Exception as e:
            if logger: logger.log_event("system_log", "TelemetryAPI", {"event": "benchmark_error", "model": req.model_name, "error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))

# Monta o frontend estático na raiz (Abaixo das rotas da API para não dar conflito)
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("telemetry_api:app", host="0.0.0.0", port=8000, reload=True)
