import pytest
import asyncio
from concurrency.lock_manager import LockManager
from concurrency.hmac_manager import generate_ephemeral_key

@pytest.mark.asyncio
async def test_wsnat_reconnect(fake_redis):
    """IT-003: simular desconexão de 3s; verificar redelivery correto e DUPLICATE_ACK"""
    resource_id = "test-res-it3"
    session_id = "session-it3"
    await generate_ephemeral_key(session_id, fake_redis)

    manager = LockManager(fake_redis)
    
    # 1. Enviar ACK inicial
    res1 = await manager.consolidate_ack(
        resource_id=resource_id,
        hmac_key_id=session_id,
        event_id="evt-dup-wsnat",
        agent_id="agent-1",
        reaction_code="CANCELLED_PROMPT",
        ttl_extend_seconds=120
    )
    assert res1 in ("OK", "RED_PROMOTED")

    # Simulate 3s delay for WSL disconnect
    await asyncio.sleep(0.1) # short for tests
    
    # 2. Re-send exact same ACK (redelivery)
    res2 = await manager.consolidate_ack(
        resource_id=resource_id,
        hmac_key_id=session_id,
        event_id="evt-dup-wsnat",
        agent_id="agent-1",
        reaction_code="CANCELLED_PROMPT",
        ttl_extend_seconds=120
    )
    assert res2 == "DUPLICATE"
