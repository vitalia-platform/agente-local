# test_redis.py | Atualizado em: 27-06-2026 11:42:03(GMT-04:00)
import os
import redis
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

r = redis.Redis(
    host='localhost', 
    port=int(os.getenv('REDIS_PORT', 6379)), 
    password=os.getenv('REDIS_PASSWORD', 'secret'), 
    db=0
)
print(r.ping())
