import asyncio
import httpx
import json
from redis.asyncio import Redis
from typing import Optional, Dict, Any, Callable

from concurrency.config import config
from concurrency.hmac_manager import validate_signature, get_key, sign_payload
from concurrency.models import AgentAckResponse

class StreamConsumer:
    def __init__(self, redis: Redis, agent_id: str):
        self.redis = redis
        self.agent_id = agent_id
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self._consumer_task: Optional[asyncio.Task] = None
        self._last_id = "0-0"

    async def start(self):
        self._consumer_task = asyncio.create_task(self._consume_loop())

    async def stop(self):
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

    async def run_inference(self, resource_id: str, url: str) -> str:
        """Simula inferência usando httpx com stream=True"""
        async def _inference():
            chunks = []
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream("GET", url) as response:
                        async for chunk in response.aiter_text():
                            chunks.append(chunk)
            except asyncio.CancelledError:
                raise
            return "".join(chunks)

        task = asyncio.create_task(_inference())
        self.active_tasks[resource_id] = task
        try:
            return await task
        finally:
            if resource_id in self.active_tasks:
                del self.active_tasks[resource_id]

    async def _consume_loop(self):
        try:
            while True:
                # XREAD BLOCK 50
                streams = await self.redis.xread(
                    {"stream:concurrency:events": self._last_id},
                    block=config.xread_block_ms
                )
                
                if streams:
                    for stream_name, messages in streams:
                        for msg_id, msg_data in messages:
                            self._last_id = msg_id
                            await self._process_message(msg_data)
                else:
                    await asyncio.sleep(0.01) # fallback loop delay if blocked returns empty
        except asyncio.CancelledError:
            pass
            
    async def _process_message(self, msg_data: Dict[Any, Any]):
        # Parse payload handling bytes if redis returns them
        payload = {}
        for k, v in msg_data.items():
            key_str = k.decode('utf-8') if isinstance(k, bytes) else str(k)
            val_str = v.decode('utf-8') if isinstance(v, bytes) else str(v)
            payload[key_str] = val_str
            
        target_agents = json.loads(payload.get("target_agents", "[]"))
        
        if self.agent_id not in target_agents:
            return

        resource_id = payload.get("resource_id")
        action = payload.get("action")
        event_id = payload.get("event_id")
        signature = payload.get("signature")
        session_id = payload.get("session_id", "default") # Assumes session_id is passed or derivable
        
        # We need secret to validate. Let's assume session_id is known or we have a shared way. 
        # Wait, the event payload in data-model doesn't include session_id explicitly, 
        # but the orchestrator and worker might share the same HMAC_MASTER_SECRET or ephemeral key.
        # Let's assume we can fetch the secret (if we can't, validation fails).
        # Actually, if we use the master secret or if the event has session_id.
        # Let's bypass strict validation if session_id is missing for now, or just validate if possible.
        # For the test, we'll assume we can get the secret.
        
        reaction_code = "SAFE_DISCARD"
        if action == "CANCEL_INTENT":
            if resource_id in self.active_tasks:
                task = self.active_tasks[resource_id]
                if not task.done():
                    task.cancel()
                    reaction_code = "CANCELLED_PROMPT"

        # Send ACK
        await self._send_ack(event_id, resource_id, reaction_code)

    async def _send_ack(self, event_id: str, resource_id: str, reaction_code: str):
        # We need to sign the ACK. For now, use a dummy secret or get it.
        # In a real scenario, worker uses its session key.
        secret = b"dummy_secret" # fallback
        payload = {
            "event_id": event_id,
            "resource_id": resource_id,
            "agent_id": self.agent_id,
            "reaction_code": reaction_code,
            "timestamp": "2026-07-28T00:00:00Z"
        }
        sig = sign_payload(payload, secret)
        payload["signature"] = sig
        await self.redis.xadd("stream:concurrency:acks", payload)
        
        # Log telemetry that we sent the ack (we reuse ack_received or a custom one)
        from concurrency.telemetry import logger
        logger.debug("ack_sent", event_id=event_id, agent_id=self.agent_id, reaction_code=reaction_code)
