# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from io import BytesIO
from elevenlabs.client import ElevenLabs
import openai
import os
import base64
import json
import requests
import logging

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
# DID_API_KEY = os.getenv("DID_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

openai.api_key = OPENAI_API_KEY

# ---------------------------
# App & CORS
# ---------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")

# Optional: initialize ElevenLabs SDK (not used in /tts below, but available)
elevenlabs = ElevenLabs(api_key=ELEVEN_API_KEY)

# ---------------------------
# Health
# ---------------------------
@app.get("/")
def home():
    return {"message": "Backend is running!"}

# ---------------------------
# Speech-to-Text (OpenAI Whisper)
# ---------------------------
@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        bio = BytesIO(audio_bytes)
        bio.name = file.filename or "audio.webm"  # Whisper requires a filename

        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=bio
        )
        return {"text": transcription.text}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("STT error")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ---------------------------
# Chat (OpenAI)
# ---------------------------
@app.post("/chat")
async def chat(prompt: str = Form(...)):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        logger.exception("Chat error")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ---------------------------
# Text-to-Speech (ElevenLabs via requests for clear errors)
# ---------------------------
@app.post("/tts")
async def text_to_speech(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Missing 'text'")

    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVEN_API_KEY is missing")

    voice_id = "JBFqnCBsd6RMkjVDRZzb"         # known-good demo voice
    model_id = "eleven_multilingual_v2"

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {"text": text, "model_id": model_id}

        r = requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=60)

        ct = r.headers.get("content-type", "")
        if r.status_code != 200:
            # Log up to 2KB of body for debugging
            body_preview = r.text[:2048] if ("json" in ct or "text" in ct) else f"<{ct} {len(r.content)} bytes>"
            logger.error(f"ElevenLabs error {r.status_code} CT={ct}: {body_preview}")
            return JSONResponse(
                status_code=502,
                content={
                    "error": "TTS provider error",
                    "status": r.status_code,
                    "content_type": ct,
                    "body": body_preview,
                },
            )

        audio_bytes = b"".join(r.iter_content(chunk_size=8192))
        if not audio_bytes:
            raise HTTPException(status_code=502, detail="Empty audio from TTS provider")

        # Return raw MP3 bytes (no need to save a file)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="speech.mp3"',  # hint name only
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
        logger.exception("TTS unexpected error")
        return JSONResponse(status_code=502, content={"error": str(e)})

# ---------------------------
# D-ID WebRTC Offer Proxy
# ---------------------------

# @app.post("/did/offer")
# async def did_offer(request: Request):
#     if not DID_API_KEY:
#         logger.error("D-ID API key missing")
#         return JSONResponse(status_code=500, content={"error": "D-ID API key missing"})

#     try:
#         offer = await request.json()
#         logger.info(f"Received offer: {offer}")
#     except Exception as e:
#         logger.error(f"Invalid JSON body: {e}")
#         raise HTTPException(status_code=400, detail="Invalid JSON body")

#     if "sdp" not in offer or "type" not in offer:
#         logger.error(f"Missing SDP or type in offer: {offer}")
#         raise HTTPException(status_code=400, detail="Missing SDP or type")

#     # D-ID API key needs Base64 encoding for Basic auth
#     encoded_key = base64.b64encode(DID_API_KEY.encode()).decode()
#     headers = {
#         "Authorization": f"Basic {encoded_key}",
#         "Content-Type": "application/json"
#     }

#     # STEP 1: Create a new stream WITH source_url
#     create_url = "https://api.d-id.com/talks/streams"
#     create_body = {
#         "source_url": "https://raw.githubusercontent.com/gafur55/Interactive-AI-Agent/main/avatar.png"
#     }
    
#     logger.info(f"Creating D-ID stream with body: {create_body}")
#     logger.info(f"Using headers: {dict(headers)}")  # Don't log the actual API key
    
#     try:
#         create_resp = requests.post(create_url, headers=headers, json=create_body, timeout=30)
#         logger.info(f"D-ID stream creation response: Status={create_resp.status_code}")
#         logger.info(f"D-ID stream creation response body: {create_resp.text}")
#     except requests.RequestException as e:
#         logger.error(f"Network error creating stream: {e}")
#         return JSONResponse(status_code=502, content={"error": "Network error creating stream"})

#     if create_resp.status_code != 201:
#         logger.error(f"Stream creation failed: {create_resp.status_code} - {create_resp.text}")
#         return JSONResponse(
#             status_code=create_resp.status_code,
#             content={"error": "Failed to create stream", "details": create_resp.text},
#         )

#     try:
#         stream = create_resp.json()
#         logger.info(f"Stream created successfully: {stream}")
#     except json.JSONDecodeError as e:
#         logger.error(f"Invalid JSON in stream response: {e}")
#         return JSONResponse(status_code=500, content={"error": "Invalid JSON from D-ID API"})

#     stream_id = stream.get("id")
#     if not stream_id:
#         logger.error(f"No stream_id in response: {stream}")
#         return JSONResponse(status_code=500, content={"error": "No stream_id returned", "details": stream})

#     # STEP 2: Send SDP offer with session_id
#     sdp_url = f"https://api.d-id.com/talks/streams/{stream_id}/sdp"
    
#     # Extract session_id from the stream response
#     session_id = stream.get("session_id", "")
    
#     # Add session_id to headers
#     sdp_headers = headers.copy()
#     if session_id:
#         sdp_headers["Cookie"] = session_id
#         logger.info(f"Added session_id cookie: {session_id[:50]}...")  # Log first 50 chars
    
#     sdp_body = {
#         "answer": {  # D-ID expects "answer" for the SDP response
#             "sdp": offer["sdp"],
#             "type": offer["type"]
#         }
#     }

#     logger.info(f"Sending SDP to {sdp_url} with body: {sdp_body}")
#     logger.info(f"SDP headers: {dict(sdp_headers)}")

#     try:
#         sdp_resp = requests.post(sdp_url, headers=sdp_headers, json=sdp_body, timeout=30)
#         logger.info(f"SDP response: Status={sdp_resp.status_code}")
#         logger.info(f"SDP response body: {sdp_resp.text}")
#     except requests.RequestException as e:
#         logger.error(f"Network error sending SDP: {e}")
#         return JSONResponse(status_code=502, content={"error": "Network error sending SDP"})

#     if sdp_resp.status_code != 200:
#         logger.error(f"SDP submission failed: {sdp_resp.status_code} - {sdp_resp.text}")
#         return JSONResponse(
#             status_code=sdp_resp.status_code,
#             content={"error": "Failed to send SDP", "details": sdp_resp.text},
#         )

#     try:
#         sdp_result = sdp_resp.json()
#         logger.info(f"SDP successful: {sdp_result}")
#     except json.JSONDecodeError as e:
#         logger.error(f"Invalid JSON in SDP response: {e}")
#         return JSONResponse(status_code=500, content={"error": "Invalid JSON from D-ID SDP API"})

#     return {
#         "stream_id": stream_id,
#         "answer": sdp_result
#     }








#-----------------------
# Heygen API Usage
# ----------------------

@app.post("/heygen/avatar")
async def heygen_avatar(request: Request):
    # Send text/avatar/voice request to HeyGen and get a video_id

    if not HEYGEN_API_KEY:
        raise HTTPException(status_code=500, detail="HEYGEN_API_KEY missing")
    
    try:
        body = await request.json()
        url = "https://api.heygen.com/v2/video/generate"

        headers = {
            "X-Api-Key": HEYGEN_API_KEY,
            "Content-Type": "application/json"
        }

        r = requests.post(url, headers=headers, json=body, timeout=60)
        r.raise_for_status()

        return r.json()
    except requests.RequestException as e:
        logger.error(f"HeyGen generate error: {e}")
        return JSONResponse(status_code=502, content={"error": str(e)})



@app.get("/heygen/status/{video_id}")
async def heygen_status(video_id: str):
    # Check HeyGen video rendering status

    url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"

    headers = {"X-Api-Key": HEYGEN_API_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()  # HeyGen returns { "error": null, "data": { "status": ..., "video_url": ... } }
    
    except requests.RequestException as e:
        logger.error(f"HeyGen status error: {e}")
        return JSONResponse(status_code=502, content={"error": str(e)})



@app.get("/heygen/download/{video_id}")
async def heygen_download(video_id: str):
    # Download finished video from HeyGen to local file

    status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    headers = {"X-Api-Key": HEYGEN_API_KEY}


    try:
        # checking the status of the url    
        r = requests.get(status_url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]

        if data.get("status") != "completed":
            return {"message": f"Video not ready yet, status: {data.get('status')}"}
        
        video_url = data.get("video_url")
        if not video_url:
            return {"error": "No video_url in HeyGen response"}
        
        video_resp = requests.get(video_url, stream=True)
        video_resp.raise_for_status()


        filename = f"heygen_{video_id}.mp4"
        filepath = os.path.join(os.getcwd(), filename)

        with open(filepath, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return {"message": "Video downloaded", "file": filepath}
    
    except Exception as e:
        logger.error(f"HeyGen download error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
