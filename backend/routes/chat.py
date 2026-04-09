from fastapi import APIRouter
from datetime import datetime, timezone
from models.message import ChatRequest
from config.db import messages_collection
from services.chatbot import detect_intent, generate_response
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

    history = get_memory(req.session_id)
    intent = detect_intent(req.message)
    reply = generate_response(intent)

    bot_msg = {
        "user_id": req.user_id,
        "session_id": req.session_id,
        "message": reply,
        "sender": "bot",
        "intent": intent,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    messages_collection.insert_one(bot_msg)
    save_to_memory(req.session_id, {"sender": "bot", "message": reply, "intent": intent})

    return {"reply": reply, "intent": intent}
