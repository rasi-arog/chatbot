from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: str
    message: str
    lat: Optional[float] = None
    lng: Optional[float] = None

class SessionRenameRequest(BaseModel):
    title: str
