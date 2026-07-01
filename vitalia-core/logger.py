# logger.py | Atualizado em: 01-07-2026 15:03:06(GMT-04:00)
import os
import json
import redis
import socket
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

REDIS_PASS = os.getenv("REDIS_PASSWORD", "secret")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://:{REDIS_PASS}@localhost:{REDIS_PORT}/0"

class EventLogger:
    def __init__(self):
        try:
            self.r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        except Exception as e:
            print(f"Erro ao conectar ao Redis para log: {e}")
            self.r = None

        # Configura o stream unificado
        self.stream_name = "vitalia_events"
        
        # Identificação da Máquina (Shards)
        self.machine_id = self._get_machine_id()
        
        # Garante a existência do diretório de armazenamento
        self.storage_dir = os.path.join(os.path.dirname(__file__), '../.specify/memory/data_storage/shards')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.shard_file = os.path.join(self.storage_dir, f"{self.machine_id}.jsonl")

    def _get_machine_id(self) -> str:
        hostname = socket.gethostname()
        machines_file = os.path.join(os.path.dirname(__file__), '../.specify/memory/session/machines.json')
        if os.path.exists(machines_file):
            try:
                with open(machines_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for mid, info in data.get("machines", {}).items():
                    if info.get("name") == hostname:
                        return mid
            except Exception:
                pass
        # Fallback
        return hashlib.md5(hostname.encode()).hexdigest()[:8]

    def log_event(self, event_type: str, source: str, payload: dict):
        """
        Adiciona um evento ao Unified Event Bus e salva no shard persistente local.
        event_type: 'conversation' | 'telemetry' | 'system_log' | 'reasoning' | 'tool_call'
        """
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "source": source,
            "payload": json.dumps(payload)
        }
        
        # 1. Publica no Redis (Event Bus)
        if self.r:
            try:
                self.r.xadd(self.stream_name, event_data, maxlen=50000)
            except Exception as e:
                print(f"Falha ao escrever no Unified Event Bus (Redis): {e}")

        # 2. Persiste fisicamente no Shard (Auditoria)
        # Filtramos telemetria de uso intensivo se desejado, mas o plano diz: "Dados auditáveis..."
        # O ideal é persistir tudo, mas vamos garantir o append rápido.
        try:
            with open(self.shard_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + "\n")
        except Exception as e:
            print(f"Falha ao gravar no shard {self.shard_file}: {e}")

# Instância global para ser importada facilmente
logger = EventLogger()

