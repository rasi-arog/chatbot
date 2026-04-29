from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.auth import router as auth_router
import tempfile
import shutil
import os
import subprocess
from groq import Groq

app = FastAPI()

_allowed_origins = [o for o in [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    os.getenv("FRONTEND_URL", ""),
    os.getenv("FRONTEND_URL_2", ""),
    os.getenv("FRONTEND_URL_3", ""),
] if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(auth_router)

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(file.file, tmp)
        webm_path = tmp.name
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        with open(webm_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(file.filename or "audio.webm", f),
                model="whisper-large-v3",
                language="en",
            )
        return {"text": transcription.text.strip()}
    except Exception as e:
        print(f"[TRANSCRIBE ERROR] {e}")
        return {"text": ""}
    finally:
        os.remove(webm_path)

@app.get("/")
def home():
    return {"message": "Healthcare chatbot backend running"}
