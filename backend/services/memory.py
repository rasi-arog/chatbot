from config.db import redis_client
import json

def save_to_memory(session_id, message):
    key = f"chat:{session_id}"
    existing = redis_client.get(key)
    data = json.loads(existing) if existing else []
    data.append(message)
    redis_client.set(key, json.dumps(data))

def get_memory(session_id):
    data = redis_client.get(f"chat:{session_id}")
    return json.loads(data) if data else []
