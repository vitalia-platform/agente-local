import pytest
import asyncio
from concurrency.lock_manager import LockManager
from concurrency.stream_consumer import StreamConsumer
from concurrency.hmac_manager import generate_ephemeral_key

@pytest.mark.asyncio
async def test_full_handshake(fake_redis):
    """IT-001: handshake completo PROPOSING_RED -> 100% ACKs -> RED com 2 workers"""
    resource_id = "test-res-it1"
    session_id = "session-it1"
    await generate_ephemeral_key(session_id, fake_redis)

    manager = LockManager(fake_redis)
    worker1 = StreamConsumer(fake_redis, "agent-1")
    worker2 = StreamConsumer(fake_redis, "agent-2")
    
    await worker1.start()
    await worker2.start()

    await manager.promote_to_yellow(resource_id, "orchestrator")

    async def dummy_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    t1 = asyncio.create_task(dummy_task())
    t2 = asyncio.create_task(dummy_task())
    worker1.active_tasks[resource_id] = t1
    worker2.active_tasks[resource_id] = t2

    await manager.propose_red(resource_id, "orchestrator", session_id, target_agents=["agent-1", "agent-2"])
    
    # Wait for processing
    await asyncio.sleep(0.2)

    assert t1.cancelled()
    assert t2.cancelled()

    acks = await fake_redis.xread({"stream:concurrency:acks": "0-0"}, count=10)
    assert len(acks) > 0
    assert len(acks[0][1]) == 2

    await worker1.stop()
    await worker2.stop()
