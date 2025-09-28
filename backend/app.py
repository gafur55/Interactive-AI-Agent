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
import base64







# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


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



# Tools for GPT
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_spotify",
            "description": "Search for songs, artists, or playlists on Spotify",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query like artist or song"},
                    "type_": {"type": "string", "enum": ["track", "artist", "playlist"], "description": "Type of search"}
                },
                "required": ["query"]
            }
        }
    }
]


@app.post("/chat")
async def chat(
    prompt: str = Form(...),
    session_id: str = Form("default")
):
    try:
        # Initialize session with conversational rules
        if session_id not in sessions:
            sessions[session_id] = [
                {
                    "role": "system",
                    "content": (
                        "You are DJ Nova, a fun, conversational music expert AI avatar. "
                        "Rules: "
                        "1. Keep answers short (1–2 sentences max). "
                        "2. Use casual, natural language with fillers (like 'gotcha', 'oh nice', 'hmm'). "
                        "3. If sharing music from Spotify, present it like you’re chatting with a friend, not a search engine. "
                        "   - Instead of 'Here are three tracks:' → say something like 'Gotcha, check these out:' "
                        "   - Mention artist + vibe in plain words, not bullet points. "
                        "   - Always drop the Spotify link inline with the track name. "
                        "4. End with a quick follow-up question (like 'Want me to pull more like that?' or 'Should I grab a playlist too?'). "
                        "5. If the user asks for tracks → use Spotify type=track. "
                        "   If they ask for playlists → type=playlist. "
                        "   If they ask for artists → type=artist. "
                        "   If they ask for albums → type=album. "
                        "6. Never make up songs or artists — only use Spotify results. "
                    ),
                }
            ]

        # Add user message
        sessions[session_id].append({"role": "user", "content": prompt})

        # Call GPT with tool definition
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=sessions[session_id],
            tools=tools
        )

        choice = response.choices[0]
        message = choice.message

        # --- CASE 1: GPT calls one or more tools ---
        if message.tool_calls:
            sessions[session_id].append(message)  # Save tool request

            for tool_call in message.tool_calls:
                logger.info(f"Tool call: {tool_call.function.name} with args {tool_call.function.arguments}")

                if tool_call.function.name == "search_spotify":
                    args = json.loads(tool_call.function.arguments)
                    raw = search_spotify(args["query"], args.get("type_", "track"))
                    formatted = format_spotify_results(raw)

                    # Always respond with a JSON object {results: [...]}
                    sessions[session_id].append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"results": formatted})
                    })

                else:
                    sessions[session_id].append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": "Unsupported tool"})
                    })

            # ✅ Only after responding to ALL tool calls, continue the chat
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=sessions[session_id],
            )
            reply = response.choices[0].message.content

        # --- CASE 2: Normal conversation ---
        else:
            reply = message.content

        # Save assistant reply
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




# -------------------------------
# spotify related
# -------------------------------


def get_spotify_token():
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {"Authorization": f"Basic {b64_auth_str}"}
    data = {"grant_type": "client_credentials"}

    r = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def search_spotify(query: str, type_: str = "track", limit: int = 3):
    token = get_spotify_token()
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query, "type": type_, "limit": limit}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()




def format_spotify_results(raw):
    results = []

    if "tracks" in raw:
        for t in raw["tracks"]["items"][:3]:
            url = t.get("external_urls", {}).get("spotify")
            if not url:
                continue
            results.append({
                "name": t["name"],
                "artist": t["artists"][0]["name"],
                "url": url
            })

    elif "playlists" in raw:
        for p in raw["playlists"]["items"][:3]:
            url = p.get("external_urls", {}).get("spotify")
            if not url:
                continue
            results.append({
                "name": p["name"],
                "artist": "Playlist",
                "url": url
            })

    elif "artists" in raw:
        for a in raw["artists"]["items"][:3]:
            url = a.get("external_urls", {}).get("spotify")
            if not url:
                continue
            results.append({
                "name": a["name"],
                "artist": "Artist",
                "url": url
            })

    elif "albums" in raw:
        for al in raw["albums"]["items"][:3]:
            url = al.get("external_urls", {}).get("spotify")
            if not url:
                continue
            results.append({
                "name": al["name"],
                "artist": al["artists"][0]["name"],
                "url": url
            })

    return results




@app.get("/spotify/search")
def spotify_search(query: str, type_: str = "track"):
    try:
        raw = search_spotify(query, type_)
        return format_spotify_results(raw)
    except Exception as e:
        logger.exception("Spotify search error")
        return JSONResponse(status_code=500, content={"error": str(e)})