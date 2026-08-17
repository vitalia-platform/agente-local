import hmac
import hashlib
import secrets
import json
from datetime import datetime, timezone
from redis.asyncio import Redis
from typing import Any, Dict

from .models import EphemeralHMACKey
from .config import config

def sign_payload(payload: Dict[str, Any], secret: bytes) -> str:
    """
    Assina o payload usando HMAC-SHA256 e o segredo fornecido.
    A chave 'signature' é removida do payload antes de assinar.
    """
    payload_copy = payload.copy()
    payload_copy.pop("signature", None)
    
    # Sort keys to ensure deterministic serialization
    serialized = json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))
    
    mac = hmac.new(secret, msg=serialized.encode('utf-8'), digestmod=hashlib.sha256)
    return mac.hexdigest()

def validate_signature(payload: Dict[str, Any], signature: str, secret: bytes) -> bool:
    """
    Valida se a assinatura confere com o payload e o segredo.
    """
    expected_signature = sign_payload(payload, secret)
    return hmac.compare_digest(expected_signature, signature)

async def generate_ephemeral_key(session_id: str, redis: Redis) -> EphemeralHMACKey:
    """
    Gera uma chave HMAC efêmera e salva no Redis.
    """
    secret = secrets.token_bytes(32)
    key = EphemeralHMACKey(session_id=session_id, secret=secret)
    
    redis_key = f"vitalia:hmac:session:{session_id}"
    await redis.set(
        redis_key, 
        secret.hex(), 
        ex=config.hmac_key_ttl_seconds
    )
    return key

async def get_key(session_id: str, redis: Redis) -> bytes | None:
    """
    Recupera o segredo HMAC da sessão do Redis.
    """
    redis_key = f"vitalia:hmac:session:{session_id}"
    secret_hex = await redis.get(redis_key)
    if not secret_hex:
        return None
    if isinstance(secret_hex, bytes):
        secret_hex = secret_hex.decode('utf-8')
    return bytes.fromhex(secret_hex)
