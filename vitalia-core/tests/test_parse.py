import json

def is_tool_call(content):
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "name" in data:
            return True
    except:
        pass
    return False

print(is_tool_call('{"name": "read_working_memory", "arguments": {"filepath": ""}}'))
