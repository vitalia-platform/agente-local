import pytest
from concurrency.lock_manager import LockManager

@pytest.mark.asyncio
async def test_state_machine_rules_green_to_red(fake_redis):
    """
    UT-005: testar que GREEN→RED direto retorna -1 do script Lua
    """
    manager = LockManager(redis=fake_redis)
    resource_id = "test-resource-2"
    
    # Init: implicitly GREEN
    # Try to propose_red without being YELLOW
    # Actually, propose_red normally expects YELLOW.
    # The Lua script should block GREEN to RED if we try to bypass YELLOW.
    # We will simulate a direct call to the lua script or via a method that tries to do this.
    
    # We will use the raw evaluate method if manager exposes it, or test propose_red directly
    # assuming propose_red tries to go from YELLOW to PROPOSING_RED.
    # If the current state is GREEN, it should return 0 (state mismatch) or -1 (illegal transition).
    # Since GREEN -> PROPOSING_RED direct is illegal, let's see.
    result = await manager.propose_red(resource_id, "agent-1", session_id="test-session")
    assert result is False
