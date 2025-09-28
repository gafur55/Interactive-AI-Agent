# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from io import BytesIO
from elevenlabs.client import ElevenLabs
import openai
import os
import json
import requests
import logging

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")
if not ELEVEN_API_KEY:
    # We don't crash here, but /tts will error if called
    logging.getLogger("uvicorn.error").warning("ELEVEN_API_KEY is missing")

openai.api_key = OPENAI_API_KEY

# ---------------------------
# App & CORS
# ---------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")

# Optional ElevenLabs SDK (not required for /tts below)
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
        bio.name = file.filename or "audio.webm"  # Whisper needs a filename

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
# Text-to-Speech (ElevenLabs via raw requests)
# ---------------------------
@app.post("/tts")
async def text_to_speech(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Missing 'text'")

    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVEN_API_KEY is missing")

    voice_id = "JBFqnCBsd6RMkjVDRZzb"  # Demo voice; replace if you like
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
        logger.exception("TTS unexpected error")
        return JSONResponse(status_code=502, content={"error": str(e)})

# --------------------------- new codes

# --- HeyGen: generate -> status -> stream (no local download) ---
import os
import time
import json
import requests
import logging
from typing import Optional
from pathlib import Path

from fastapi import Form, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("uvicorn.error")

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
if not HEYGEN_API_KEY:
    logger.warning("HEYGEN_API_KEY is missing; /heygen/* routes will fail if called.")

def _hg_headers(json_ct: bool = True):
    if not HEYGEN_API_KEY:
        raise HTTPException(status_code=500, detail="HEYGEN_API_KEY is missing")
    h = {"X-Api-Key": HEYGEN_API_KEY}
    if json_ct:
        h["Content-Type"] = "application/json"
    return h

def _probe_cdn_has_bytes(url: str, max_tries: int = 12, sleep_s: float = 1.5) -> int:
    """Wait until CDN actually serves bytes; return content length if known (>0)."""
    for _ in range(max_tries):
        try:
            h = requests.head(url, timeout=15, allow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0",
                                       "Accept": "video/mp4,*/*"})
            cl = h.headers.get("Content-Length") or h.headers.get("content-length")
            if h.status_code == 200 and cl and int(cl) > 0:
                return int(cl)
            # tiny range probe
            r = requests.get(url, timeout=15,
                             headers={"Range": "bytes=0-1",
                                      "User-Agent": "Mozilla/5.0",
                                      "Accept": "video/mp4,*/*"})
            if r.status_code in (200, 206) and r.content:
                return max(int(cl or 0), len(r.content))
        except Exception:
            pass
        time.sleep(sleep_s)
    return 0

@app.post("/heygen/generate")
async def heygen_generate(
    input_text: str = Form(...),
    # Use your own ID here; by default we assume TALKING PHOTO flow
    avatar_id: str = Form("af5820d3e6bb42609e4782cc89db0aee"),
    character_type: str = Form("talking_photo"),  # "talking_photo" | "avatar"
    voice_id: str = Form("2d5b0e6cf36f460aa7fc47e3eee4ba54"),
    avatar_style: str = Form("normal"),
    bg_type: str = Form("color"),
    bg_value: str = Form("#008000"),
    width: int = Form(1280),
    height: int = Form(720),
):
    """
    Start a HeyGen render and return { video_id }.
    - If character_type == 'talking_photo': avatar_id is your Talking Photo ID
    - If character_type == 'avatar':        avatar_id is a template/public avatar id
    """
    try:
        char = (
            {"type": "talking_photo", "talking_photo_id": avatar_id, "avatar_style": avatar_style}
            if character_type == "talking_photo"
            else {"type": "avatar", "avatar_id": avatar_id, "avatar_style": avatar_style}
        )

        payload = {
            "video_inputs": [
                {
                    "character": char,
                    "voice": {"type": "text", "input_text": input_text, "voice_id": voice_id},
                    "background": {"type": bg_type, "value": bg_value},
                }
            ],
            "dimension": {"width": width, "height": height},
        }

        r = requests.post(
            "https://api.heygen.com/v2/video/generate",
            headers=_hg_headers(),
            data=json.dumps(payload),
            timeout=60,
        )
        if r.status_code != 200:
            try:
                err = r.json()
            except Exception:
                err = {"raw": r.text[:2048]}
            logger.error(f"[HeyGen] generate failed: {err}")
            return JSONResponse(status_code=502, content={"error": "generate failed", "details": err})

        data = r.json()
        vid = (data.get("data") or {}).get("video_id")
        if not vid:
            return JSONResponse(status_code=502, content={"error": "missing video_id", "raw": data})
        return {"video_id": vid}

    except Exception as e:
        logger.exception("heygen_generate error")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/heygen/status")
async def heygen_status(video_id: str):
    """Pass-through single status check (no waiting)."""
    try:
        url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        r = requests.get(url, headers={"X-Api-Key": HEYGEN_API_KEY}, timeout=30)
        if r.status_code != 200:
            try:
                err = r.json()
            except Exception:
                err = {"raw": r.text[:2048]}
            return JSONResponse(status_code=502, content={"error": "status failed", "details": err})
        return r.json()
    except Exception as e:
        logger.exception("heygen_status error")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/heygen/stream")
async def heygen_stream(
    request: Request,
    video_id: str,
    poll_interval: int = 3,
    max_wait_seconds: int = 900,
):
    """
    Waits until HeyGen marks the job 'completed', then streams the MP4 bytes.
    Forwards Range header to support seeking in the <video> element.
    """
    try:
        # 1) poll
        status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        started = time.time()
        video_url = None
        thumb = None

        while True:
            rs = requests.get(status_url, headers={"X-Api-Key": HEYGEN_API_KEY}, timeout=30)
            if rs.status_code != 200:
                try:
                    err = rs.json()
                except Exception:
                    err = {"raw": rs.text[:2048]}
                return JSONResponse(status_code=502, content={"error": "status failed", "details": err})

            j = rs.json()
            d = (j.get("data") or {})
            st = d.get("status")
            if st == "completed":
                video_url = d.get("video_url")
                thumb = d.get("thumbnail_url")
                if not video_url:
                    return JSONResponse(status_code=502, content={"error": "completed but no video_url", "raw": j})
                break

            if st == "failed":
                return JSONResponse(status_code=502, content={"error": "render failed", "details": d.get("error"), "raw": j})

            if (time.time() - started) > max_wait_seconds:
                return JSONResponse(
                    status_code=504,
                    content={"error": "timeout waiting for completion", "video_id": video_id, "last_status": st},
                )
            time.sleep(max(1, poll_interval))

        # 2) confirm CDN has bytes (optional)
        _probe_cdn_has_bytes(video_url, max_tries=12, sleep_s=1.5)

        # 3) stream (forward Range if the browser requests it)
        range_header = request.headers.get("range")
        up_headers = {"User-Agent": "Mozilla/5.0", "Accept": "video/mp4,*/*"}
        if range_header:
            up_headers["Range"] = range_header

        upstream = requests.get(video_url, headers=up_headers, stream=True, timeout=300)
        status_code = upstream.status_code if upstream.status_code in (200, 206) else 200

        # prepare response headers
        out_headers = {
            "Cache-Control": "no-store",
            "Accept-Ranges": upstream.headers.get("Accept-Ranges", "bytes"),
            "Content-Type": upstream.headers.get("Content-Type", "video/mp4"),
            "X-HeyGen-Video-Id": video_id,
            "X-HeyGen-Video-URL": video_url,
        }
        cl = upstream.headers.get("Content-Length")
        if cl: out_headers["Content-Length"] = cl
        cr = upstream.headers.get("Content-Range")
        if cr: out_headers["Content-Range"] = cr

        def body_iter():
            for chunk in upstream.iter_content(chunk_size=1024 * 128):
                if chunk:
                    yield chunk

        return StreamingResponse(body_iter(), status_code=status_code, headers=out_headers, media_type="video/mp4")

    except Exception as e:
        logger.exception("heygen_stream error")
        return JSONResponse(status_code=500, content={"error": str(e)})