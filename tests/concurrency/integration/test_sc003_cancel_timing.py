import pytest
import asyncio
import time
from concurrency.stream_publisher import StreamPublisher
from concurrency.stream_consumer import StreamConsumer
from concurrency.hmac_manager import generate_ephemeral_key

@pytest.mark.asyncio
async def test_sc003_cancel_timing(fake_redis):
    """IT-002: medir delta entre XREAD e asyncio.Task.cancel() < 150ms"""
    resource_id = "test-res-it2"
    session_id = "session-it2"
    await generate_ephemeral_key(session_id, fake_redis)

    worker = StreamConsumer(fake_redis, "agent-1")
    await worker.start()

    cancel_time = None
    async def dummy_task():
        nonlocal cancel_time
        try:
            print("Dummy task starting...")
            await asyncio.sleep(10)
            print("Dummy task woke up?")
        except asyncio.CancelledError:
            cancel_time = time.perf_counter()
            print(f"Dummy task cancelled at {cancel_time}")
            raise

    t = asyncio.create_task(dummy_task())
    worker.active_tasks[resource_id] = t
    
    # Let the dummy task start running
    await asyncio.sleep(0.01)

    publisher = StreamPublisher(fake_redis)
    start_time = time.perf_counter()
    print(f"Sending intent at {start_time}")
    await publisher.publish_cancel_intent(resource_id, ["agent-1"], session_id)
    
    await asyncio.sleep(0.2)
    print(f"Task cancelled state: {t.cancelled()}, cancel_time: {cancel_time}")
    assert t.cancelled()
    
    delta = cancel_time - start_time
    assert delta < 0.150
    
    await worker.stop()
