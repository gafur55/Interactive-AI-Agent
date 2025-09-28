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
# Global in-memory sessions
# ---------------------------
sessions = {}  # { session_id: [ {role, content}, ... ] }

@app.post("/chat")
async def chat(
    prompt: str = Form(...),
    session_id: str = Form("default")  # default if you don’t pass one
):
    try:
        # Initialize session if new
        if session_id not in sessions:
            sessions[session_id] = [
                {
                    "role": "system",
                    "content": (
                        "You are DJ Nova, a fun, conversational music expert AI avatar. "
                        "Rules: "
                        "1. Keep answers under 2 sentences by default. "
                        "2. Use casual, natural language with short fillers "
                        "(like 'gotcha', 'hmm', 'oh nice'). "
                        "3. When it makes sense, end with a short clarifying or follow-up question. "
                        "4. Expand only if the user explicitly asks for more detail. "
                        "5. Keep tone lively and human-like, not formal or robotic."
                    ),
                }
            ]

        # Append user message
        sessions[session_id].append({"role": "user", "content": prompt})

        # Send full conversation to GPT
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=sessions[session_id],
        )

        reply = response.choices[0].message.content

        # Append assistant reply
        sessions[session_id].append({"role": "assistant", "content": reply})

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


# ---------------------------
# HeyGen: local photo -> talking_photo -> video -> save mp4 (no AV4 required)
# ---------------------------
# ---------------------------
# HeyGen: Generate, poll, download, and local-photo test (Talking Photo)
# ---------------------------
import time
import json
import requests
from pathlib import Path
from typing import Optional
from fastapi import Form, HTTPException
from fastapi.responses import JSONResponse, Response

# =========================
# HeyGen one-shot endpoint
# =========================
import os
import time
import json
import requests
from pathlib import Path
from fastapi import Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import logging
from dotenv import load_dotenv

# Ensure env is loaded and logger exists (safe if already done earlier)
load_dotenv()
logger = logging.getLogger("uvicorn.error")

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
if not HEYGEN_API_KEY:
    logger.warning("HEYGEN_API_KEY is missing; /heygen/* routes will fail if called.")

def _probe_cdn_has_bytes(url: str, max_tries: int = 12, sleep_s: float = 1.5) -> int:
    """
    Return an expected content length (>0 if known) once CDN is ready.
    Uses HEAD and a 1-byte Range probe; retries a few times.
    """
    for _ in range(max_tries):
        try:
            h = requests.head(
                url,
                timeout=15,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "video/mp4,*/*"},
            )
            cl = h.headers.get("Content-Length") or h.headers.get("content-length")
            if h.status_code == 200 and cl and int(cl) > 0:
                return int(cl)

            # Tiny range probe: if we get even 1 byte, CDN is ready
            r = requests.get(
                url,
                timeout=15,
                headers={"Range": "bytes=0-1", "User-Agent": "Mozilla/5.0", "Accept": "video/mp4,*/*"},
            )
            if r.status_code in (200, 206) and r.content:
                return max(int(cl or 0), len(r.content))
        except Exception:
            pass
        time.sleep(sleep_s)
    return 0

@app.post("/heygen/generate_and_download")
async def heygen_generate_and_download(
    input_text: str = Form(..., description="Speech text for the avatar"),
    avatar_id: str = Form("af5820d3e6bb42609e4782cc89db0aee"),
    voice_id: str = Form("2d5b0e6cf36f460aa7fc47e3eee4ba54"),
    avatar_style: str = Form("normal"),
    bg_type: str = Form("color"),
    bg_value: str = Form("#008000"),
    width: int = Form(1280),
    height: int = Form(720),
    # File naming & polling controls
    filename: str = Form("generated_video.mp4"),
    poll_interval: int = Form(5),
    max_wait_seconds: int = Form(300),
):
    """
    1) Generate (v2)
    2) Poll status (v1) until 'completed' (handles waiting/queued/in_progress/processing/pending)
    3) Wait for CDN bytes (HEAD + Range probe)
    4) Stream MP4 to client while saving to ./downloads/<filename>
    """
    try:
        if not HEYGEN_API_KEY:
            raise HTTPException(status_code=500, detail="HEYGEN_API_KEY is missing")

        # 1) Generate
        logger.info(f"[HeyGen] Starting generation for text='{input_text[:50]}...'")
        gen_payload = {
            "video_inputs": [
                {
                    "character": {"type": "talking_photo", "talking_photo_id": avatar_id, "avatar_style": avatar_style},
                    "voice": {"type": "text", "input_text": input_text, "voice_id": voice_id},
                    "background": {"type": bg_type, "value": bg_value},
                }
            ],
            "dimension": {"width": width, "height": height},
        }
        gen = requests.post(
            "https://api.heygen.com/v2/video/generate",
            headers={"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"},
            data=json.dumps(gen_payload),
            timeout=60,
        )
        if gen.status_code != 200:
            try:
                err_json = gen.json()
            except Exception:
                err_json = {"raw": gen.text[:2048]}
            logger.error(f"[HeyGen] Generate failed: {err_json}")
            return JSONResponse(status_code=502, content={"error": "HeyGen generate failed", "details": err_json})

        gen_json = gen.json()
        video_id = (gen_json.get("data") or {}).get("video_id")
        if not video_id:
            logger.error("[HeyGen] No video_id returned")
            return JSONResponse(status_code=502, content={"error": "Missing video_id in HeyGen response", "raw": gen_json})
        logger.info(f"[HeyGen] Generation started, video_id={video_id}")

        # 2) Poll until completed
        headers = {"X-Api-Key": HEYGEN_API_KEY}
        status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        started = time.time()

        # Include all transitional states we’ve seen in the wild
        transitional = {"waiting", "queued", "in_progress", "processing", "pending", "rendering"}

        while True:
            resp = requests.get(status_url, headers=headers, timeout=30)
            if resp.status_code != 200:
                try:
                    err = resp.json()
                except Exception:
                    err = {"raw": resp.text[:2048]}
                logger.error(f"[HeyGen] Status check failed: {err}")
                return JSONResponse(status_code=502, content={"error": "Status check failed", "details": err})

            j = resp.json()
            data = (j.get("data") or {})
            status = data.get("status")
            logger.info(f"[HeyGen] video_id={video_id} status={status}")

            if status == "completed":
                video_url = data.get("video_url")
                thumbnail_url = data.get("thumbnail_url")
                if not video_url:
                    logger.error(f"[HeyGen] Completed but no video_url for video_id={video_id}")
                    return JSONResponse(status_code=502, content={"error": "No video_url in completed status", "raw": j})
                logger.info(f"[HeyGen] Video ready: {video_url}")
                break

            if status in transitional:
                # Optional: slower polling for early queue states
                if status in {"waiting", "queued"}:
                    sleep_s = max(2, int(poll_interval) * 2)
                else:
                    sleep_s = max(1, int(poll_interval))

                if (time.time() - started) > int(max_wait_seconds):
                    logger.error(f"[HeyGen] Timeout waiting for completion video_id={video_id}, last_status={status}")
                    return JSONResponse(
                        status_code=504,
                        content={
                            "error": "Timeout waiting for video to complete",
                            "video_id": video_id,
                            "last_status": status,
                            "waited_seconds": int(time.time() - started),
                        },
                    )

                time.sleep(sleep_s)
                continue

            if status == "failed":
                logger.error(f"[HeyGen] Generation failed: {data.get('error')}")
                return JSONResponse(status_code=502, content={"error": "Video generation failed", "details": data.get("error"), "raw": j})

            logger.warning(f"[HeyGen] Unexpected status={status} for video_id={video_id}")
            return JSONResponse(status_code=502, content={"error": f"Unexpected status: {status}", "raw": j})

        # 3) Wait for CDN to have bytes
        expected_len = _probe_cdn_has_bytes(video_url, max_tries=12, sleep_s=1.5)
        logger.info(f"[HeyGen] video_id={video_id} CDN content length={expected_len}")

        # 4) Stream and save
        base_dir = Path(__file__).parent.resolve()
        downloads_dir = base_dir / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        out_path = (downloads_dir / filename).resolve()
        logger.info(f"[HeyGen] Saving to {out_path}")

        upstream = requests.get(
            video_url,
            stream=True,
            timeout=300,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "video/mp4,*/*"},
        )
        if upstream.status_code not in (200, 206):
            logger.error(f"[HeyGen] Stream open failed: {upstream.status_code}")
            return JSONResponse(
                status_code=502,
                content={"error": "Failed to open video stream", "status_code": upstream.status_code, "headers": dict(upstream.headers)},
            )

        def iter_and_save():
            bytes_written = 0
            with open(out_path, "wb") as f:
                for chunk in upstream.iter_content(chunk_size=1024 * 128):
                    if not chunk:
                        continue
                    f.write(chunk)
                    bytes_written += len(chunk)
                    yield chunk
            logger.info(f"[HeyGen] Finished writing {bytes_written} bytes to {out_path}")
            if bytes_written == 0:
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass

        headers_out = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-HeyGen-Video-Id": video_id,
            "X-HeyGen-Video-URL": video_url,
            "X-Saved-Path": str(out_path),
        }
        if thumbnail_url:
            headers_out["X-HeyGen-Thumbnail-URL"] = thumbnail_url
        if expected_len:
            headers_out["Content-Length"] = str(expected_len)

        logger.info(f"[HeyGen] Streaming video_id={video_id} to client")
        return StreamingResponse(iter_and_save(), media_type="video/mp4", headers=headers_out)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[HeyGen] generate_and_download (robust) unexpected error")
        return JSONResponse(status_code=500, content={"error": str(e)})
