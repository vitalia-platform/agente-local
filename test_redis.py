import asyncio, os
from dotenv import load_dotenv
load_dotenv('.env')
import redis.asyncio as redis_async
REDIS_URL = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:{os.getenv('REDIS_PORT', 6379)}/0"
print(f"URL: {REDIS_URL}")
async def test():
    r = redis_async.Redis.from_url(REDIS_URL)
    print(await r.ping())
asyncio.run(test())
