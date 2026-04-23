from fastapi import APIRouter, UploadFile, File, Form
from datetime import datetime, timezone
import tempfile, shutil, os
from models.message import ChatRequest
from config.db import messages_collection
from services.agent import agent
from services.memory import save_to_memory, get_memory, clear_memory
from services.image_verify import verify_image

router = APIRouter()

@router.post("/chat")
def chat(req: ChatRequest):
    client_msg = {
        "user_id": req.user_id,
        "session_id": req.session_id,
        "message": req.message,
        "sender": "client",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    messages_collection.insert_one(client_msg)
    save_to_memory(req.session_id, {"sender": "client", "message": req.message})

    result = agent.invoke({
        "input": req.message,
        "session_id": req.session_id,
        "lat": req.lat,
        "lng": req.lng,
    })
    structured = result["output"]  # dict with type, message, data

    bot_msg = {
        "user_id": req.user_id,
        "session_id": req.session_id,
        "message": structured.get("message", ""),
        "type": structured.get("type", "text"),
        "structured_data": structured.get("data", {}),
        "sender": "bot",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    messages_collection.insert_one(bot_msg)
    save_to_memory(req.session_id, {"sender": "bot", "message": structured.get("message", "") if structured.get("type") in ("text", "health_advice", "doctor_suggestion") else ""})

    return structured

@router.get("/chat/sessions/{user_id}")
def get_sessions(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$session_id", "last_message": {"$first": "$created_at"}}},
        {"$sort": {"last_message": -1}},
    ]
    sessions = list(messages_collection.aggregate(pipeline))
    return {"sessions": [s["_id"] for s in sessions]}

@router.get("/chat/history/{session_id}")
def get_history(session_id: str):
    messages = list(
        messages_collection.find({"session_id": session_id}, {"_id": 0}).sort("created_at", 1)
    )
    return {"messages": messages}

@router.post("/verify-image")
async def verify_image_api(file: UploadFile = File(...), user_id: str = Form("1"), session_id: str = Form("")):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        result = verify_image(tmp_path)
        print(f"[verify-image] session_id='{session_id}' user_id='{user_id}' file='{file.filename}'")
        if session_id:
            messages_collection.insert_one({
                "user_id": user_id,
                "session_id": session_id,
                "message": file.filename,
                "sender": "client",
                "type": "image_file",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            messages_collection.insert_one({
                "user_id": user_id,
                "session_id": session_id,
                "message": result.get("message", ""),
                "type": result.get("type", "image_analysis"),
                "structured_data": result.get("data", {}),
                "sender": "bot",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            # Save image context into memory so agent can reference it in follow-up chat
            image_type = result.get("data", {}).get("image_type", "image")
            summary = f"User uploaded a {image_type}. Analysis: {result.get('message', '')[:300]}"
            save_to_memory(session_id, {"sender": "client", "message": file.filename, "type": "image_file"})
            save_to_memory(session_id, {"sender": "bot", "type": "image_analysis", "message": "", "image_summary": summary})
        return result
    except Exception as e:
        print(f"[verify-image ERROR] {e}")
        return {
            "type": "image_verification",
            "message": "Image processing failed. Please try again.",
            "data": {"is_medical": None}
        }
    finally:
        os.remove(tmp_path)

@router.delete("/chat/session/{session_id}")
def delete_session(session_id: str):
    messages_collection.delete_many({"session_id": session_id})
    clear_memory(session_id)
    return {"status": "deleted"}
