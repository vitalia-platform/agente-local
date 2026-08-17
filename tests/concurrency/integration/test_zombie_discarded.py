import pytest
import asyncio
from concurrency.lock_manager import LockManager
from concurrency.hmac_manager import generate_ephemeral_key
from concurrency.config import config

@pytest.mark.asyncio
async def test_zombie_discarded(fake_redis):
    """IT-004: iniciar handshake sem worker; verificar ZOMBIE_DISCARDED e RED"""
    resource_id = "test-res-it4"
    session_id = "session-it4"
    await generate_ephemeral_key(session_id, fake_redis)

    # config timeout in tests might be too long. We can patch it.
    config.lock_timeout_ms = 100 # very short for test
    
    manager = LockManager(fake_redis)
    await manager.promote_to_yellow(resource_id, "orchestrator")
    
    await manager.propose_red(resource_id, "orchestrator", session_id, target_agents=["agent-zombie"])
    
    # Wait for the zombie timer to expire (0.1s)
    await asyncio.sleep(0.2)
    
    # check state is RED
    state = await fake_redis.hget(f"vitalia:lock:{resource_id}", "current_state")
    if isinstance(state, bytes):
        state = state.decode('utf-8')
    assert state == "RED"
    
    # hmac key should be deleted
    ttl = await fake_redis.ttl(f"vitalia:hmac:session:{session_id}")
    assert ttl < 0
