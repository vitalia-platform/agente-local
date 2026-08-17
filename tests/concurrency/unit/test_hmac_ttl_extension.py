import pytest
import asyncio
from concurrency.config import config
from concurrency.hmac_manager import generate_ephemeral_key
from concurrency.lock_manager import LockManager

@pytest.mark.asyncio
async def test_hmac_ttl_extension(fake_redis):
    """
    UT-004: simular lock e verificar que chave HMAC tem TTL estendido
    após consolidate_acks.lua chamar EXPIRE.
    """
    # 1. Gerar chave
    session_id = "test-session-1"
    key = await generate_ephemeral_key(session_id, fake_redis)
    redis_key = f"vitalia:hmac:session:{session_id}"
    
    # TTL original deve ser config.hmac_key_ttl_seconds
    ttl_inicial = await fake_redis.ttl(redis_key)
    assert ttl_inicial > 0
    
    # 2. Simulate consolidate_acks.lua running
    manager = LockManager(redis=fake_redis)
    # Fake processing an ACK which extends TTL by 120s for example
    res = await manager.consolidate_ack(
        resource_id="res-1",
        hmac_key_id=session_id,
        event_id="evt-1",
        agent_id="agent-1",
        reaction_code="CANCELLED_PROMPT",
        ttl_extend_seconds=120
    )
    
    # Verify TTL was extended
    ttl_final = await fake_redis.ttl(redis_key)
    assert ttl_final > ttl_inicial
    assert ttl_final > 100
