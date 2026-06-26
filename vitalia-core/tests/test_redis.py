import redis
r = redis.Redis(host='localhost', port=6379, password='secret', db=0)
print(r.ping())
