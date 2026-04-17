from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
import whisper
import tempfile
import shutil
import os

app = FastAPI()

whisper_model = whisper.load_model("base")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

# Ensure winget FFmpeg is in the system PATH
ffmpeg_path = r"C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
if os.path.exists(ffmpeg_path) and ffmpeg_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] += os.pathsep + ffmpeg_path

@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        result = whisper_model.transcribe(tmp_path, fp16=False)
        return {"text": result["text"].strip()}
    except Exception as e:
        err_str = str(e)
        if "End of file" in err_str or "Failed to load audio" in err_str or "cannot reshape tensor" in err_str:
            return {"text": ""}
        raise e
    finally:
        os.remove(tmp_path)

@app.get("/")
def home():
    return {"message": "Day 2 backend running"}
