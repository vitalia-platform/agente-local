import structlog
from typing import List

logger = structlog.get_logger("vitalia.concurrency")

class ConcurrencyLogger:
    @staticmethod
    def lock_transition(resource_id: str, old_state: str, new_state: str, agent_id: str, generation_id: str = ""):
        logger.info("lock_transition", resource_id=resource_id, old_state=old_state, new_state=new_state, agent_id=agent_id, generation_id=generation_id)

    @staticmethod
    def cancel_intent_sent(resource_id: str, target_agents: List[str], event_id: str):
        logger.info("cancel_intent_sent", resource_id=resource_id, target_agents=target_agents, event_id=event_id)

    @staticmethod
    def ack_received(event_id: str, agent_id: str, reaction_code: str):
        logger.info("ack_received", event_id=event_id, agent_id=agent_id, reaction_code=reaction_code)

    @staticmethod
    def duplicate_ack_detected(event_id: str, agent_id: str, delta_ms: float = 0):
        logger.warning("duplicate_ack_detected", event_id=event_id, agent_id=agent_id, delta_ms=delta_ms)

    @staticmethod
    def zombie_discarded(resource_id: str, agent_id: str, hmac_key_id: str):
        logger.warning("zombie_discarded", resource_id=resource_id, agent_id=agent_id, hmac_key_id=hmac_key_id)

    @staticmethod
    def red_promoted(resource_id: str, event_id: str):
        logger.info("red_promoted", resource_id=resource_id, event_id=event_id)
