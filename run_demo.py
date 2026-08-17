import asyncio
import structlog
from redis.asyncio import Redis
import uuid6

from src.concurrency.config import config
from src.concurrency.lock_manager import LockManager
from src.concurrency.stream_consumer import StreamConsumer
from src.concurrency.hmac_manager import generate_ephemeral_key

# Configurar logs bonitos para o terminal
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger("demo")

async def run_worker(redis: Redis, agent_id: str):
    logger.info("Iniciando Worker", agent_id=agent_id)
    worker = StreamConsumer(redis, agent_id)
    await worker.start()
    return worker

async def main():
    redis = Redis.from_url(config.redis_url, decode_responses=False)
    
    # Limpar banco para a demo ser limpa
    await redis.flushdb()
    
    # 1. Preparar a sessão
    session_id = f"demo-session-{uuid6.uuid7()}"
    resource_id = "doc/spec-001.md"
    
    logger.info("=== 1. Iniciando Sessão ===")
    await generate_ephemeral_key(session_id, redis)
    logger.info("Chave HMAC efêmera gerada.", session_id=session_id)
    
    manager = LockManager(redis)
    
    # 2. Subir 2 workers
    logger.info("=== 2. Conectando Workers no Barramento ===")
    w1 = await run_worker(redis, "worker-1")
    w2 = await run_worker(redis, "worker-2")
    
    # 3. Mudar estado para YELLOW (Leitura Analítica)
    logger.info("=== 3. Orquestrador promove para YELLOW ===")
    await manager.promote_to_yellow(resource_id, "orchestrator")
    
    # Simular workers processando LLM (criando tasks ativas)
    async def fake_llm_inference(agent_id):
        try:
            logger.info("Iniciando inferência longa...", agent_id=agent_id)
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.warning("Inferência CANCELADA pelo barramento!", agent_id=agent_id)
            raise

    w1.active_tasks[resource_id] = asyncio.create_task(fake_llm_inference("worker-1"))
    w2.active_tasks[resource_id] = asyncio.create_task(fake_llm_inference("worker-2"))
    
    await asyncio.sleep(1) # Deixar as inferências rodarem 1 segundo
    
    # 4. Orquestrador solicita PROPOSING_RED
    logger.info("=== 4. Orquestrador precisa escrever! Solicitando PROPOSING_RED ===")
    await manager.propose_red(resource_id, "orchestrator", session_id, target_agents=["worker-1", "worker-2"])
    
    # 5. Ler ACKs recebidos (Orquestrador consolidando)
    logger.info("=== 5. Orquestrador aguardando ACKs... ===")
    acks_received = 0
    last_id = "0-0"
    
    while acks_received < 2:
        streams = await redis.xread({"stream:concurrency:acks": last_id}, count=10, block=1000)
        for stream_name, messages in streams:
            for msg_id, msg_data in messages:
                last_id = msg_id
                
                # Parse bytes to str
                payload = {k.decode(): v.decode() for k, v in msg_data.items()}
                logger.info("ACK recebido", agent_id=payload["agent_id"], reaction=payload["reaction_code"])
                
                res = await manager.consolidate_ack(
                    payload["resource_id"],
                    session_id,
                    payload["event_id"],
                    payload["agent_id"],
                    payload["reaction_code"],
                    120
                )
                acks_received += 1
                
                if res == "RED_PROMOTED" or acks_received == 2:
                    # Em nosso caso simplificado retornamos OK, e fazemos a transição manual se precisar,
                    # Mas vamos forçar o RED já que todos responderam.
                    pass
    
    logger.info("=== 6. Todos ACKs recebidos! Promovendo para RED ===")
    await manager.confirm_red(resource_id)
    
    logger.info("Simulando escrita exclusiva no arquivo (1 segundo)...")
    await asyncio.sleep(1)
    
    logger.info("=== 7. Escrita concluída, liberando para GREEN ===")
    await manager.release_red(resource_id)
    
    # Desligar tudo
    await w1.stop()
    await w2.stop()
    await redis.aclose()
    
    logger.info("=== Demo Concluída com Sucesso! ===")

if __name__ == "__main__":
    asyncio.run(main())
