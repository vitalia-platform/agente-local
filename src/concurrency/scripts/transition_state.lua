-- transition_state.lua
-- Assinatura: EVAL script 1 {resource_id} {from_state} {to_state} {agent_id} {new_generation_id}

local resource_id = KEYS[1]
local from_state = ARGV[1]
local to_state = ARGV[2]
local agent_id = ARGV[3]
local new_generation_id = ARGV[4]

-- State key
local lock_key = "vitalia:lock:" .. resource_id

-- current state defaults to GREEN if not set
local current_state = redis.call('HGET', lock_key, 'current_state')
if not current_state or current_state == false then
    current_state = 'GREEN'
end

-- Validate transition rules
if current_state == 'GREEN' and (to_state == 'PROPOSING_RED' or to_state == 'RED') then
    return -1 -- Illegal transition GREEN -> RED or PROPOSING_RED direct
end

if current_state ~= from_state then
    return 0 -- State mismatch
end

-- generation_id check if provided
if new_generation_id and new_generation_id ~= "" then
    local current_gen = redis.call('HGET', lock_key, 'generation_id')
    if current_gen and current_gen ~= false and new_generation_id <= current_gen then
        -- ABA protection: new generation must be > current
        return 0
    end
    redis.call('HSET', lock_key, 'generation_id', new_generation_id)
end

-- Apply state change
redis.call('HSET', lock_key, 'current_state', to_state)

if to_state == 'PROPOSING_RED' then
    redis.call('HSET', lock_key, 'proposing_agent_id', agent_id)
elseif to_state == 'RED' or to_state == 'GREEN' then
    -- When moving to RED or back to GREEN, clear proposing_agent_id
    redis.call('HDEL', lock_key, 'proposing_agent_id')
end

return 1
