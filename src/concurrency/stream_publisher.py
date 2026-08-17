import uuid6
from redis.asyncio import Redis
from typing import List
from pydantic import ValidationError

from concurrency.models import HandshakeStreamEvent
from concurrency.hmac_manager import sign_payload, get_key
from concurrency.config import config
from concurrency.telemetry import ConcurrencyLogger

class StreamPublisher:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def publish_cancel_intent(self, resource_id: str, target_agents: List[str], session_id: str) -> str:
        """
        Publica um evento CANCEL_INTENT no stream:concurrency:events.
        Retorna o event_id (UUID v7).
        """
        # Obter chave HMAC da sessão
        secret = await get_key(session_id, self.redis)
        if not secret:
            raise ValueError(f"Chave HMAC não encontrada para sessão {session_id}")

        event_id = str(uuid6.uuid7())
        
        # Build payload as dict to sign it
        payload = {
            "event_id": event_id,
            "resource_id": resource_id,
            "action": "CANCEL_INTENT",
            "target_agents": target_agents,
            "timeout_ms": config.lock_timeout_ms
        }
        
        signature = sign_payload(payload, secret)
        payload["signature"] = signature
        
        # Validate through Pydantic model
        event = HandshakeStreamEvent(**payload)
        
        # Publish to Redis stream
        # dict values must be string, bytes, or float for redis, so we serialize lists
        import json
        redis_payload = {
            "event_id": event.event_id,
            "resource_id": event.resource_id,
            "action": event.action,
            "target_agents": json.dumps(event.target_agents),
            "timeout_ms": str(event.timeout_ms),
            "signature": event.signature
        }
        
        await self.redis.xadd("stream:concurrency:events", redis_payload)
        ConcurrencyLogger.cancel_intent_sent(resource_id, target_agents, event_id)
        return event_id
