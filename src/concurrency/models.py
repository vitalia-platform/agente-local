import uuid6
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime, timezone

def generate_uuid7() -> str:
    return str(uuid6.uuid7())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class LockState(BaseModel):
    resource_id: str = Field(..., description="Identificador do arquivo SDD ou código-fonte")
    current_state: Literal["GREEN", "YELLOW", "PROPOSING_RED", "RED"] = Field(..., description="Estado atual da máquina de estados")
    generation_id: str = Field(default_factory=generate_uuid7, description="Versão do recurso (UUID v7)")
    active_analytical_agents: List[str] = Field(default_factory=list, description="IDs dos agentes em leitura analítica ativa")
    proposing_agent_id: Optional[str] = Field(default=None, description="ID do agente solicitando escrita exclusiva")

class HandshakeStreamEvent(BaseModel):
    event_id: str = Field(default_factory=generate_uuid7, description="UUID v7 do evento")
    resource_id: str = Field(..., description="Recurso alvo")
    action: Literal["CANCEL_INTENT", "LOCK_RELEASED"] = Field(..., description="Tipo de evento")
    target_agents: List[str] = Field(..., description="Agentes que DEVEM responder com ACK")
    timeout_ms: int = Field(default=5000, description="TTL antes de ZOMBIE_DISCARDED")
    signature: str = Field(..., description="Assinatura HMAC-SHA256 hex")

class AgentAckResponse(BaseModel):
    event_id: str = Field(..., description="UUID v7 do evento original")
    resource_id: str = Field(..., description="Recurso alvo")
    agent_id: str = Field(..., description="ID do agente respondendo")
    reaction_code: Literal["SAFE_DISCARD", "CANCELLED_PROMPT", "PARTIAL_STATE_FLUSH", "ZOMBIE_DISCARDED", "DUPLICATE_ACK"] = Field(..., description="Código de reação")
    timestamp: datetime = Field(default_factory=utc_now, description="Momento do ACK em UTC")
    signature: str = Field(..., description="Assinatura HMAC-SHA256 hex")

class EphemeralHMACKey(BaseModel):
    session_id: str = Field(..., description="ID da sessão")
    secret: bytes = Field(..., description="32 bytes aleatórios")
    created_at: datetime = Field(default_factory=utc_now, description="Data de criação")
