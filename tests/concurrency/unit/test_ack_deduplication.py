import pytest
from concurrency.lock_manager import LockManager
from concurrency.hmac_manager import generate_ephemeral_key

@pytest.mark.asyncio
async def test_ack_deduplication(fake_redis):
    """
    UT-002: enviar mesmo event_id duas vezes; 
    verificar 1ª retorna OK (ou RED_PROMOTED), 2ª retorna DUPLICATE.
    """
    manager = LockManager(redis=fake_redis)
    session_id = "test-session-2"
    await generate_ephemeral_key(session_id, fake_redis)
    
    event_id = "evt-dup-1"
    
    res1 = await manager.consolidate_ack(
        resource_id="res-2",
        hmac_key_id=session_id,
        event_id=event_id,
        agent_id="agent-1",
        reaction_code="CANCELLED_PROMPT",
        ttl_extend_seconds=120
    )
    
    assert res1 in ("OK", "RED_PROMOTED")
    
    res2 = await manager.consolidate_ack(
        resource_id="res-2",
        hmac_key_id=session_id,
        event_id=event_id,
        agent_id="agent-1",
        reaction_code="CANCELLED_PROMPT",
        ttl_extend_seconds=120
    )
    
    assert res2 == "DUPLICATE"
