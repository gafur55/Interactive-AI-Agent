from fastapi import FastAPI, UploadFile, File
import openai, os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO



# Load environment variables
load_dotenv()

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Allow React frontend (localhost:3000) to talk to FastAPI (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Backend is running!"}

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    # Convert upload to file-like object
    audio_bytes = await file.read()
    audio_file = BytesIO(audio_bytes)
    audio_file.name = file.filename  # Whisper requires a name

    try:
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return {"text": transcription.text}
    except Exception as e:
        return {"error": str(e)}