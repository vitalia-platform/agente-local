-- consolidate_acks.lua
-- Assinatura: EVAL script 2 {resource_id} {hmac_key_id} {event_id} {agent_id} {reaction_code} {ttl_extend_seconds}

local resource_id = KEYS[1]
local hmac_key_id = KEYS[2]
local event_id = ARGV[1]
local agent_id = ARGV[2]
local reaction_code = ARGV[3]
local ttl_extend_seconds = ARGV[4]

local ack_key = "vitalia:ack:processed:" .. event_id

local is_duplicate = redis.call('SISMEMBER', ack_key, agent_id)
if is_duplicate == 1 then
    return "DUPLICATE"
end

redis.call('SADD', ack_key, agent_id)
redis.call('EXPIRE', ack_key, 6) -- 5s + 1s

-- Simulating RED_PROMOTED for tests if needed, or just OK
local lock_key = "vitalia:lock:" .. resource_id
-- We would check if pending count == 0 here and promote to RED
-- For now, just return OK and extend HMAC TTL

local hmac_key = "vitalia:hmac:session:" .. hmac_key_id
redis.call('EXPIRE', hmac_key, ttl_extend_seconds)

return "OK"
