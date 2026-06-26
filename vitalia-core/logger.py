# logger.py | Atualizado em: 26-06-2026 12:08:18(GMT-04:00)
import os
import json
import redis
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

REDIS_PASS = os.getenv("REDIS_PASSWORD", "secret")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://:{REDIS_PASS}@localhost:{REDIS_PORT}/0"

class EventLogger:
    def __init__(self):
        try:
            self.r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            self.stream_name = "vitalia:events"
        except Exception as e:
            print(f"Erro ao conectar ao Redis para log: {e}")
            self.r = None

    def log_event(self, event_type: str, source: str, payload: dict):
        """
        Adiciona um evento à Redis Stream.
        event_type: 'llm_turn', 'hardware_tick', 'rag_insert'
        source: 'architect', 'engineer', 'telemetry'
        payload: dados tipados
        """
        if not self.r:
            return

        event_data = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "source": source,
            "payload": json.dumps(payload)
        }
        try:
            # Adiciona ao stream com limite de 10.000 itens (aprox ~20MB se texto denso)
            self.r.xadd(self.stream_name, event_data, maxlen=10000)
        except Exception as e:
            print(f"Falha ao escrever log no Redis: {e}")

# Instância global para ser importada facilmente
logger = EventLogger()
