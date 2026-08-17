import os
import pytest
import pytest_asyncio
import fakeredis.aioredis
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()

@pytest_asyncio.fixture
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()

@pytest_asyncio.fixture
async def real_redis():
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set in environment")
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception as e:
        pytest.skip(f"Could not connect to real Redis: {e}")
    yield redis
    await redis.aclose()
