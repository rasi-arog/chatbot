from fastapi import APIRouter
from datetime import datetime, timezone
from models.message import ChatRequest
from config.db import messages_collection
from services.agent import agent
from services.memory import save_to_memory, get_memory

router = APIRouter()

@router.post("/chat")
def chat(req: ChatRequest):
    client_msg = {
        "user_id": req.user_id,
        "session_id": req.session_id,
        "message": req.message,
        "sender": "client",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    messages_collection.insert_one(client_msg)
    save_to_memory(req.session_id, {"sender": "client", "message": req.message})

    reply = agent.invoke({"input": req.message, "session_id": req.session_id})["output"]

    bot_msg = {
        "user_id": req.user_id,
        "session_id": req.session_id,
        "message": reply,
        "sender": "bot",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    messages_collection.insert_one(bot_msg)
    save_to_memory(req.session_id, {"sender": "bot", "message": reply})

    return {"reply": reply}
