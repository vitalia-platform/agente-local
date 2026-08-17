-- zombie_cleanup.lua
-- Assinatura: EVAL script 1 {resource_id} {agent_id} {hmac_key_id}

local resource_id = KEYS[1]
local agent_id = ARGV[1]
local hmac_key_id = ARGV[2]

-- 1. Registra reação ZOMBIE_DISCARDED (simulado)
-- Normally we would add to a stream or log this in Redis.
-- 2. Revoga vitalia:hmac:session:{hmac_key_id} via DEL
local hmac_key = "vitalia:hmac:session:" .. hmac_key_id
redis.call('DEL', hmac_key)

-- 3. Promove estado para RED_EXCLUSIVE_WRITE (barreira forçada)
local lock_key = "vitalia:lock:" .. resource_id
redis.call('HSET', lock_key, 'current_state', 'RED')
redis.call('HDEL', lock_key, 'proposing_agent_id')

return 1
