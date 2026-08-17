import asyncio
import os
from redis.asyncio import Redis
from dotenv import load_dotenv

async def main():
    load_dotenv()
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    print(f"Connecting to {redis_url}...")
    try:
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        info = await redis.info()
        print(f"Connected successfully! Redis version: {info.get('redis_version')}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
    finally:
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(main())
