<<<<<<< HEAD
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
=======
import logging

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, JSONResponse
import openai, os, requests
from dotenv import load_dotenv
>>>>>>> fc0a869eee26d3e89643ae469e4f0ffadb5f183c
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from io import BytesIO
from elevenlabs.client import ElevenLabs
import openai, os
from fastapi import HTTPException, Form
from fastapi.responses import Response, JSONResponse
import os, json, requests
from io import BytesIO
import logging

# Load env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

app = FastAPI()

<<<<<<< HEAD
=======
DID_API_KEY = os.getenv("DID_API_KEY")

openai.api_key = os.getenv("OPENAI_API_KEY")

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")        

# Init ElevenLabs client
elevenlabs = ElevenLabs(api_key=ELEVEN_API_KEY)

# Allow React frontend (localhost:3000) to talk to FastAPI (localhost:8000)
>>>>>>> fc0a869eee26d3e89643ae469e4f0ffadb5f183c
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

elevenlabs = ElevenLabs(api_key=ELEVEN_API_KEY)

@app.get("/")
def home():
    return {"message": "Backend is running!"}

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        bio = BytesIO(audio_bytes)
        bio.name = file.filename or "audio.webm"

        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=bio
        )
        return {"text": transcription.text}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/chat")
async def chat(prompt: str = Form(...)):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

logger = logging.getLogger("uvicorn.error")

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

@app.post("/tts")
async def text_to_speech(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Missing 'text'")
    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVEN_API_KEY is missing")

    voice_id = "JBFqnCBsd6RMkjVDRZzb"
    model_id = "eleven_multilingual_v2"

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": model_id,
        }

        r = requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=60)
        ct = r.headers.get("content-type", "")
        if r.status_code != 200:
            # Log up to 2KB of body for debugging
            body_text = r.text[:2048] if "application/json" in ct or "text/" in ct else f"<{ct} {len(r.content)} bytes>"
            logger.error(f"ElevenLabs error {r.status_code} CT={ct}: {body_text}")
            return JSONResponse(status_code=502, content={
                "error": "TTS provider error",
                "status": r.status_code,
                "content_type": ct,
                "body": body_text,
            })

        audio_bytes = b"".join(r.iter_content(chunk_size=8192))
        if not audio_bytes:
            raise HTTPException(status_code=502, detail="Empty audio from TTS provider")

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="speech.mp3"',
                "Cache-Control": "no-store",
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(audio_bytes)),
            },
        )

    except requests.Timeout:
        logger.exception("TTS timeout")
        raise HTTPException(status_code=504, detail="TTS timed out")
    except requests.RequestException as e:
        logger.exception("TTS network error")
        raise HTTPException(status_code=502, detail=f"TTS network error: {e}")
    except Exception as e:
<<<<<<< HEAD
        logger.exception("TTS unexpected error")
        return JSONResponse(status_code=502, content={"error": str(e)})
=======
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
>>>>>>> fc0a869eee26d3e89643ae469e4f0ffadb5f183c
