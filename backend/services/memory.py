import json

_fallback: dict = {}

try:
    from config.db import redis_client
    redis_client.ping()
    _use_redis = True
except Exception:
    _use_redis = False
    print("[MEMORY] Redis unavailable — using in-memory fallback")

def _get(session_id: str) -> list:
    if _use_redis:
        try:
            data = redis_client.get(f"chat:{session_id}")
            return json.loads(data) if data else []
        except Exception:
            pass
    return _fallback.get(session_id, [])

def _set(session_id: str, data: list):
    if _use_redis:
        try:
            redis_client.set(f"chat:{session_id}", json.dumps(data))
            return
        except Exception:
            pass
    _fallback[session_id] = data

def save_to_memory(session_id: str, message: dict):
    data = _get(session_id)
    data.append(message)
    _set(session_id, data[-20:])  # keep last 20 messages

def get_memory(session_id: str) -> list:
    return _get(session_id)

def clear_memory(session_id: str):
    if _use_redis:
        try:
            redis_client.delete(f"chat:{session_id}")
        except Exception:
            pass
    _fallback.pop(session_id, None)
