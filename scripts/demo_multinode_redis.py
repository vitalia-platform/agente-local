#!/usr/bin/env python3
"""
Simples Teste de Interação Multimáquinas via Redis Streams e Ollama
Ignora o ecossistema Autogen (devido à reformulação) para provar a viabilidade da arquitetura.

Uso:
  Nó 1 (Publisher): python3 scripts/demo_multinode_redis.py --mode publisher --redis-host 127.0.0.1
  Nó 2 (Consumer):  python3 scripts/demo_multinode_redis.py --mode consumer --redis-host 192.168.0.211 --model qwen2.5-coder:7b
"""

import argparse
import json
import time
import uuid
try:
    import redis
    import httpx
except ImportError:
    print("Por favor, instale as dependências mínimas: pip install redis httpx")
    exit(1)

STREAM_TASKS = "vitalia:test:tasks"
STREAM_RESULTS = "vitalia:test:results"

def call_ollama(prompt, model, host, port):
    url = f"http://{host}:{port}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    print(f"[*] Chamando modelo {model} em {host}:{port}...")
    resp = httpx.post(url, json=payload, timeout=60.0)
    if resp.status_code != 200:
        raise Exception(f"Erro {resp.status_code}: {resp.text}")
    return resp.json().get("response", "")

def run_publisher(r):
    task_id = str(uuid.uuid4())
    prompt = "Responda em uma frase: Qual é o principal benefício de usar filas do Redis em sistemas distribuídos?"
    
    print(f"[Publisher] Enviando tarefa {task_id} para o stream {STREAM_TASKS}")
    r.xadd(STREAM_TASKS, {"task_id": task_id, "prompt": prompt})
    
    print("[Publisher] Aguardando resultado...")
    last_id = "$"
    while True:
        messages = r.xread({STREAM_RESULTS: last_id}, block=2000, count=1)
        if messages:
            for stream, msgs in messages:
                for msg_id, msg_data in msgs:
                    data = {k.decode(): v.decode() for k, v in msg_data.items()}
                    if data.get("task_id") == task_id:
                        print("\n✅ [Publisher] Resultado recebido do Nó 2:")
                        print(f"> Modelo Usado: {data.get('model')}")
                        print(f"> Resposta: {data.get('response')}")
                        return
                    last_id = msg_id
        else:
            print(".", end="", flush=True)

def run_consumer(r, args):
    print(f"[Consumer] Escutando o stream {STREAM_TASKS} (Pressione Ctrl+C para sair)...")
    last_id = "$"
    while True:
        messages = r.xread({STREAM_TASKS: last_id}, block=0, count=1)
        for stream, msgs in messages:
            for msg_id, msg_data in msgs:
                data = {k.decode(): v.decode() for k, v in msg_data.items()}
                task_id = data.get("task_id")
                prompt = data.get("prompt")
                
                print(f"\n[Consumer] Tarefa {task_id} recebida! Processando...")
                
                try:
                    response = call_ollama(prompt, args.model, args.ollama_host, args.ollama_port)
                    
                    print(f"[Consumer] Respondendo para {STREAM_RESULTS}...")
                    r.xadd(STREAM_RESULTS, {
                        "task_id": task_id, 
                        "model": args.model, 
                        "response": response
                    })
                except Exception as e:
                    print(f"❌ Erro ao chamar Ollama: {e}")
                
                last_id = msg_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["publisher", "consumer"], required=True)
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--redis-pass", default="vitalia_redis_secure_2026")
    parser.add_argument("--ollama-host", default="127.0.0.1")
    parser.add_argument("--ollama-port", type=int, default=11434)
    parser.add_argument("--model", default="llama3.2:latest")
    
    args = parser.parse_args()
    
    r = redis.Redis(host=args.redis_host, port=args.redis_port, password=args.redis_pass)
    
    try:
        r.ping()
    except Exception as e:
        print(f"❌ Não foi possível conectar ao Redis em {args.redis_host}:{args.redis_port}: {e}")
        exit(1)

    if args.mode == "publisher":
        run_publisher(r)
    else:
        run_consumer(r, args)
