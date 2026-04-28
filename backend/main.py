from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.auth import router as auth_router
import whisper
import tempfile
import shutil
import os
import subprocess

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
app.include_router(auth_router)

@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(file.file, tmp)
        webm_path = tmp.name

    wav_path = webm_path.replace(".webm", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        result = whisper_model.transcribe(wav_path, fp16=False, temperature=0, language="en")
        return {"text": result["text"].strip()}
    except subprocess.CalledProcessError:
        return {"text": ""}
    except Exception as e:
        err_str = str(e)
        if "End of file" in err_str or "Failed to load audio" in err_str or "cannot reshape tensor" in err_str:
            return {"text": ""}
        raise e
    finally:
        os.remove(webm_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

@app.get("/")
def home():
    return {"message": "Day 2 backend running"}
