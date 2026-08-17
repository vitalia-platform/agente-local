#!/usr/bin/env python3
"""
Script de validação de rede entre nós do Vitalia.
Uso no Nó 2: python3 scripts/check_multinode.py --redis-host 192.168.0.211 --ollama-host localhost
"""

import argparse
import socket
import sys

try:
    import redis
    import httpx
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("Aviso: 'redis' ou 'httpx' não instalados. Testando apenas TCP básico.")

def check_tcp(host, port, name):
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"✅ [{name}] Conexão TCP aberta em {host}:{port}")
            return True
    except Exception as e:
        print(f"❌ [{name}] Falha na conexão TCP para {host}:{port} - {e}")
        return False

def check_redis_ping(host, port, password):
    if not HAS_DEPS: return
    try:
        r = redis.Redis(host=host, port=port, password=password, socket_timeout=3)
        if r.ping():
            print(f"✅ [Redis] Autenticação e PING bem sucedidos em {host}:{port}")
    except Exception as e:
        print(f"❌ [Redis] Falha ao testar PING: {e}")

def check_ollama(host, port):
    if not HAS_DEPS: return
    try:
        url = f"http://{host}:{port}/api/tags"
        resp = httpx.get(url, timeout=3)
        if resp.status_code == 200:
            print(f"✅ [Ollama] API respondendo em {url}")
            models = [m['name'] for m in resp.json().get('models', [])]
            print(f"   Modelos encontrados: {', '.join(models)}")
        else:
            print(f"❌ [Ollama] Status {resp.status_code} na API {url}")
    except Exception as e:
        print(f"❌ [Ollama] Falha na API HTTP: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--redis-pass", default="vitalia_redis_secure_2026")
    parser.add_argument("--ollama-host", default="127.0.0.1")
    parser.add_argument("--ollama-port", type=int, default=11434)
    args = parser.parse_args()

    print("--- Diagnosticando Nós do Vitalia ---")
    
    tcp_redis = check_tcp(args.redis_host, args.redis_port, "Redis")
    tcp_ollama = check_tcp(args.ollama_host, args.ollama_port, "Ollama")
    
    if HAS_DEPS:
        if tcp_redis:
            check_redis_ping(args.redis_host, args.redis_port, args.redis_pass)
        if tcp_ollama:
            check_ollama(args.ollama_host, args.ollama_port)
    else:
        print("\nPara testes completos (ping, auth, models), instale as libs:")
        print("pip install redis httpx")
