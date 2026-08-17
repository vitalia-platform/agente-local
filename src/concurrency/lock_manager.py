import os
import uuid6
from redis.asyncio import Redis

class LockManager:
    def __init__(self, redis: Redis):
        self.redis = redis
        # Load script content
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'transition_state.lua')
        with open(script_path, 'r') as f:
            self._transition_script_content = f.read()
        self._transition_script = self.redis.register_script(self._transition_script_content)

        # Load consolidate_acks script
        consolidate_path = os.path.join(os.path.dirname(__file__), 'scripts', 'consolidate_acks.lua')
        with open(consolidate_path, 'r') as f:
            self._consolidate_script = self.redis.register_script(f.read())

        # Load zombie_cleanup script
        zombie_path = os.path.join(os.path.dirname(__file__), 'scripts', 'zombie_cleanup.lua')
        with open(zombie_path, 'r') as f:
            self._zombie_script = self.redis.register_script(f.read())

    async def promote_to_yellow(self, resource_id: str, agent_id: str) -> bool:
        res = await self._transition_script(
            keys=[resource_id],
            args=["GREEN", "YELLOW", agent_id, ""]
        )
        if res == 1:
            from concurrency.telemetry import ConcurrencyLogger
            ConcurrencyLogger.lock_transition(resource_id, "GREEN", "YELLOW", agent_id)
        return res == 1

    async def propose_red(self, resource_id: str, agent_id: str, session_id: str, target_agents: list = None) -> bool:
        new_gen = str(uuid6.uuid7())
        res = await self._transition_script(
            keys=[resource_id],
            args=["YELLOW", "PROPOSING_RED", agent_id, new_gen]
        )
        if res == 1:
            from concurrency.stream_publisher import StreamPublisher
            import asyncio
            from concurrency.config import config
            
            # Send CANCEL_INTENT
            publisher = StreamPublisher(self.redis)
            target_agents = target_agents or []
            if target_agents:
                await publisher.publish_cancel_intent(resource_id, target_agents, session_id)
                
                # Schedule zombie cleanup
                async def zombie_timer():
                    try:
                        await asyncio.sleep(config.lock_timeout_ms / 1000.0)
                        # For each target agent, call cleanup_zombie
                        for ta in target_agents:
                            await self.cleanup_zombie(resource_id, ta, session_id)
                    except asyncio.CancelledError:
                        pass
                
                if not hasattr(self, "_zombie_timers"):
                    self._zombie_timers = {}
                self._zombie_timers[resource_id] = asyncio.create_task(zombie_timer())
                
        return res == 1

    async def confirm_red(self, resource_id: str) -> bool:
        res = await self._transition_script(
            keys=[resource_id],
            args=["PROPOSING_RED", "RED", "", ""]
        )
        if res == 1:
            from concurrency.telemetry import ConcurrencyLogger
            ConcurrencyLogger.lock_transition(resource_id, "PROPOSING_RED", "RED", "")
            
            # Cancel zombie timer if it exists
            timer = getattr(self, "_zombie_timers", {}).pop(resource_id, None)
            if timer and not timer.done():
                timer.cancel()
                
        return res == 1

    async def release_red(self, resource_id: str) -> bool:
        res = await self._transition_script(
            keys=[resource_id],
            args=["RED", "GREEN", "", ""]
        )
        if res == 1:
            from concurrency.telemetry import ConcurrencyLogger
            ConcurrencyLogger.lock_transition(resource_id, "RED", "GREEN", "")
        return res == 1

    async def consolidate_ack(self, resource_id: str, hmac_key_id: str, event_id: str, agent_id: str, reaction_code: str, ttl_extend_seconds: int):
        res = await self._consolidate_script(
            keys=[resource_id, hmac_key_id],
            args=[event_id, agent_id, reaction_code, ttl_extend_seconds]
        )
        if isinstance(res, bytes):
            res = res.decode('utf-8')
            
        from concurrency.telemetry import ConcurrencyLogger
        if res == "DUPLICATE":
            ConcurrencyLogger.duplicate_ack_detected(event_id, agent_id, 0)
        else:
            ConcurrencyLogger.ack_received(event_id, agent_id, reaction_code)
            
        return res

    async def cleanup_zombie(self, resource_id: str, agent_id: str, hmac_key_id: str):
        res = await self._zombie_script(
            keys=[resource_id],
            args=[agent_id, hmac_key_id]
        )
        if res == 1:
            from concurrency.telemetry import ConcurrencyLogger
            ConcurrencyLogger.zombie_discarded(resource_id, agent_id, hmac_key_id)
        return res == 1
