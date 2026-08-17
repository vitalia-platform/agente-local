import pytest
import asyncio
import uuid6
from concurrency.lock_manager import LockManager

@pytest.mark.asyncio
async def test_lua_transitions(fake_redis):
    """
    UT-001: testar transição sequencial GREEN→YELLOW→PROPOSING_RED→RED
    com tasks concorrentes para verificar atomicidade.
    """
    manager = LockManager(redis=fake_redis)
    resource_id = "test-resource-1"
    
    # Init: GREEN is default for non-existent.
    # Transition to YELLOW
    success = await manager.promote_to_yellow(resource_id, "agent-1")
    assert success is True
    
    # Concurrently try to transition to PROPOSING_RED from YELLOW
    async def try_propose(agent_id):
        return await manager.propose_red(resource_id, agent_id, session_id="test-session")
        
    results = await asyncio.gather(*(try_propose(f"agent-{i}") for i in range(10)))
    
    # Only one should succeed
    successes = [r for r in results if r is True]
    assert len(successes) == 1
    
    # Now it is in PROPOSING_RED, confirm to RED
    success = await manager.confirm_red(resource_id)
    assert success is True
    
    # Release to GREEN
    success = await manager.release_red(resource_id)
    assert success is True
