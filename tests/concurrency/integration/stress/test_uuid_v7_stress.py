import pytest
import uuid6
import asyncio

@pytest.mark.asyncio
async def test_uuid_v7_stress():
    """LT-002: gerar 1000 UUID v7; verificar monotonicidade e zero colisão"""
    uuids = []
    
    # Generate 1000 fast to check collisions and sequence handling
    for _ in range(1000):
        uuids.append(str(uuid6.uuid7()))
        
    # Check no collisions
    assert len(set(uuids)) == 1000
    
    # Check strictly monotonic
    for i in range(1, len(uuids)):
        assert uuids[i] > uuids[i-1]
