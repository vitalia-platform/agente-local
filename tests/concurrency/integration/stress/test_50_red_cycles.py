import pytest
import asyncio
from concurrency.lock_manager import LockManager
from concurrency.stream_consumer import StreamConsumer
from concurrency.hmac_manager import generate_ephemeral_key

@pytest.mark.asyncio
async def test_50_red_cycles(fake_redis):
    """LT-001: 50 ciclos YELLOW -> RED -> GREEN no mesmo recurso"""
    resource_id = "test-res-stress"
    session_id = "session-stress"
    await generate_ephemeral_key(session_id, fake_redis)

    from concurrency.config import config
    config.lock_timeout_ms = 1000  # 1s so it doesn't fire before we call confirm_red

    manager = LockManager(fake_redis)
    worker = StreamConsumer(fake_redis, "agent-1")
    await worker.start()

    initial_tasks_count = len(asyncio.all_tasks())

    for i in range(50):
        await manager.promote_to_yellow(resource_id, "orchestrator")
        
        async def dummy():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise
            finally:
                if resource_id in worker.active_tasks:
                    del worker.active_tasks[resource_id]
        
        t = asyncio.create_task(dummy())
        worker.active_tasks[resource_id] = t
        
        # let it start
        await asyncio.sleep(0.01)
        
        await manager.propose_red(resource_id, "orchestrator", session_id, target_agents=["agent-1"])
        
        # wait for cancel
        await asyncio.sleep(0.02)
        assert t.cancelled()
        
        await manager.confirm_red(resource_id)
        await manager.release_red(resource_id)
        
    await worker.stop()
    
    assert len(worker.active_tasks) == 0
    
    # Ensure no 50 tasks leaked
    final_tasks_count = len(asyncio.all_tasks())
    assert final_tasks_count < initial_tasks_count + 10
