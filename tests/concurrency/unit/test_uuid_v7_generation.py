import pytest
import uuid6

def test_uuid_v7_generation_monotonic():
    """
    UT-003: Verify that generated UUIDv7s are monotonic and their lexicographical
    comparison holds true for sequentially generated values.
    """
    uuids = [str(uuid6.uuid7()) for _ in range(1000)]
    
    # Check that they are strictly increasing
    for i in range(len(uuids) - 1):
        assert uuids[i] < uuids[i+1], f"UUIDs not monotonic: {uuids[i]} >= {uuids[i+1]}"

    # Verify formatting (UUIDv7 looks like a standard UUID)
    assert len(uuids[0]) == 36
    assert uuids[0].count("-") == 4
