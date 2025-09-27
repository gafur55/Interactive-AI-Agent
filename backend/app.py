import logging

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, JSONResponse
import openai, os, requests
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from elevenlabs.client import ElevenLabs 


# Load environment variables
load_dotenv()

app = FastAPI()

DID_API_KEY = os.getenv("DID_API_KEY")

openai.api_key = os.getenv("OPENAI_API_KEY")

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")        

# Init ElevenLabs client
elevenlabs = ElevenLabs(api_key=ELEVEN_API_KEY)

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
    

@app.post("/chat")
async def chat(prompt: str = Form(...)):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",   # or "gpt-4o" if you want full GPT-4o
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        return {"error": str(e)}




@app.post("/tts")
async def text_to_speech(text: str = Form(...)):
    """
    Convert text into speech using ElevenLabs official SDK.
    Returns MP3 audio.
    """
    try:
        audio_stream = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",  # Example voice_id
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        # audio_stream is a generator, so we need to collect bytes
        audio_bytes = b"".join(audio_stream)

        return StreamingResponse(BytesIO(audio_bytes), media_type="audio/mpeg")

    except Exception as e:
        return {"error": str(e)}
    


@app.post("/did/offer")
async def did_offer(request: Request):
    payload = {
        "source_url": "https://raw.githubusercontent.com/gafur55/Interactive-AI-Agent/main/avatar.png",
        "voice": "en-US_AllisonV3Voice",
    }

    if not DID_API_KEY:
        logging.error("DID_API_KEY environment variable is not set")
        return JSONResponse(
            status_code=500,
            content={"error": "D-ID API key is not configured"},
        )

    offer = await request.json()
    url = "https://api.d-id.com/talks/streams/webrtc"
    headers = {
        "Authorization": f"Basic {DID_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {**payload, "offer": offer}

    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.exception("D-ID offer request failed")
        status_code = getattr(exc.response, "status_code", 502)
        detail = {
            "error": "Failed to initialize D-ID WebRTC session",
            "details": str(exc),
        }
        if exc.response is not None:
            try:
                detail["response"] = exc.response.json()
            except ValueError:
                detail["response_text"] = exc.response.text
        return JSONResponse(status_code=status_code, content=detail)

    return response.json()
