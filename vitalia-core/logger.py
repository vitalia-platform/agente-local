# logger.py | Atualizado em: 31-07-2026 (Refatorado para SDD Observability Phase 2)
import os
import json
import redis
import socket
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
from config_manager import config

class EventLogger:
    def __init__(self):
        try:
            self.r = redis.Redis.from_url(config.get_redis_url(), decode_responses=True)
        except Exception as e:
            print(f"Erro ao conectar ao Redis para log: {e}")
            self.r = None

        self.stream_name = "vitalia_events"
        self.machine_id = self._get_machine_id()
        
        # Inicializa a criptografia (Artigo V)
        self.fernet = self._init_cryptography()
        
        # Fallback de gravação
        self.storage_dir = self._get_storage_dir()
        self.shard_file = self.storage_dir / f"{self.machine_id}.jsonl"

    def _init_cryptography(self) -> Fernet:
        secret = os.getenv("HMAC_MASTER_SECRET", os.getenv("DASHBOARD_SECRET_KEY", "vitalia-fallback-secret-2026"))
        # Fernet requires 32 url-safe base64-encoded bytes
        key = hashlib.sha256(secret.encode()).digest()
        b64_key = base64.urlsafe_b64encode(key)
        return Fernet(b64_key)

    def _get_storage_dir(self) -> Path:
        try:
            if config.shards_dir and config.shards_dir.exists():
                return config.shards_dir
        except:
            pass
        
        fallback_dir = Path(os.path.join(os.path.dirname(__file__), '../logs'))
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir

    def _get_machine_id(self) -> str:
        hostname = socket.gethostname()
        try:
            machines_file = config.machines_file
            if machines_file.exists():
                with open(machines_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for mid, info in data.get("machines", {}).items():
                    if info.get("name") == hostname:
                        return mid
        except:
            pass
        return hashlib.md5(hostname.encode()).hexdigest()[:8]

    def log_event(self, event_type: str, source: str, payload: dict):
        """
        Adiciona um evento ao Unified Event Bus e salva no shard persistente local.
        A carga útil é sempre criptografada antes do tráfego ou gravação.
        """
        try:
            payload_json = json.dumps(payload)
            encrypted_payload = self.fernet.encrypt(payload_json.encode()).decode('utf-8')
        except Exception as e:
            encrypted_payload = f"ENCRYPTION_ERROR: {str(e)}"
            
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "source": source,
            "payload": encrypted_payload
        }
        
        if self.r:
            try:
                self.r.xadd(self.stream_name, event_data, maxlen=50000)
            except Exception as e:
                print(f"Falha ao escrever no Unified Event Bus (Redis): {e}")

        try:
            with open(self.shard_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + "\n")
        except Exception as e:
            print(f"Falha ao gravar no shard {self.shard_file}: {e}")

    def decrypt_payload(self, encrypted_str: str) -> dict:
        """
        Descriptografa uma string criptografada pelo log_event devolvendo o dicionário original.
        """
        if not isinstance(encrypted_str, str) or encrypted_str.startswith("ENCRYPTION_ERROR"):
            return {"error": str(encrypted_str)}
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_str.encode('utf-8'))
            return json.loads(decrypted_bytes.decode('utf-8'))
        except Exception as e:
            return {"error": f"DECRYPTION_FAILED: {str(e)}"}

logger = EventLogger()
