import json
import logging
import base64
import cv2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from config import config
from services.openai_service import openai_service
from services.spotify_service import spotify_service
from services.herdora_service import herdora_service
from utils.session_manager import session_manager
from utils.text_utils import strip_links_for_tts




# ---------------------------
# App Initialization
# ---------------------------
app = FastAPI(title="DJ Vivian API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")



# ---------------------------
# GPT Tool Definitions
# ---------------------------
CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_spotify",
            "description": "Search for songs, artists, or playlists on Spotify",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query like artist or song"
                    },
                    "type_": {
                        "type": "string",
                        "enum": ["track", "artist", "playlist", "album"],
                        "description": "Type of search"
                    }
                },
                "required": ["query"]
            }
        }
    }
]



# ---------------------------
# Pydantic Models
# ---------------------------
class HerdoraRequest(BaseModel):
    image_base64: str
    prompt: str = "Describe this image."
    max_tokens: int = 256

class HerdoraTextRequest(BaseModel):
    hedora_text: str



# ---------------------------
# Health Check
# ---------------------------
@app.get("/")
def home():
    """Health check endpoint"""
    return {"message": "Backend is running!", "status": "healthy"}



# ---------------------------
# Speech-to-Text Endpoint
# ---------------------------
@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Convert audio to text using OpenAI Whisper.
    
    Args:
        file: Audio file upload
        
    Returns:
        JSON with transcribed text
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        text = openai_service.transcribe_audio(
            audio_bytes,
            filename=file.filename or "audio.webm"
        )
        return {"text": text}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("STT error")
        return JSONResponse(status_code=500, content={"error": str(e)})



# ---------------------------
# Text-to-Speech Endpoint
# ---------------------------
@app.post("/tts")
async def text_to_speech(text: str = Form(...)):
    """
    Convert text to speech using OpenAI TTS.
    Removes Spotify links before processing.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        Audio file (MP3)
    """
    # Clean text (remove Spotify links)
    clean_text = strip_links_for_tts(text)
    
    if not clean_text.strip():
        raise HTTPException(status_code=400, detail="Missing or empty text")
    
    try:
        audio_bytes = openai_service.text_to_speech(clean_text)
        
        if not audio_bytes:
            raise HTTPException(status_code=502, detail="Empty audio from TTS")
        
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
    
    except Exception as e:
        logger.exception("TTS error")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")



# ---------------------------
# Chat Endpoint
# ---------------------------
@app.post("/chat")
async def chat(
    prompt: str = Form(...),
    session_id: str = Form("default")
):
    """
    Chat with DJ Vivian. Supports Spotify tool calling.
    
    Args:
        prompt: User message
        session_id: Session identifier for conversation history
        
    Returns:
        JSON with assistant's reply
    """
    try:
        # Get session and add user message
        messages = session_manager.get_session(session_id)
        session_manager.add_message(session_id, "user", prompt)
        
        # Get initial GPT response
        response = openai_service.chat_completion(messages, tools=CHAT_TOOLS)
        choice = response.choices[0]
        message = choice.message
        
        # Handle tool calls (Spotify search)
        if message.tool_calls:
            # Add assistant's tool request to session
            messages.append(message)
            
            # Process each tool call
            for tool_call in message.tool_calls:
                try:
                    logger.info(
                        f"Tool call: {tool_call.function.name} "
                        f"with args {tool_call.function.arguments}"
                    )
                    
                    if tool_call.function.name == "search_spotify":
                        # Parse arguments
                        args = json.loads(tool_call.function.arguments)
                        query = args["query"]
                        search_type = args.get("type_", "track")
                        
                        # Search Spotify
                        raw_results = spotify_service.search(query, search_type)
                        formatted_results = spotify_service.format_results(raw_results)
                        
                        # Add tool response to session
                        session_manager.add_tool_message(
                            session_id,
                            tool_call.id,
                            json.dumps(formatted_results)
                        )
                    else:
                        # Unknown tool
                        session_manager.add_tool_message(
                            session_id,
                            tool_call.id,
                            json.dumps({"error": f"Unknown tool {tool_call.function.name}"})
                        )
                
                except Exception as e:
                    logger.exception("Tool handling error")
                    session_manager.add_tool_message(
                        session_id,
                        tool_call.id,
                        json.dumps({"error": str(e)})
                    )
            
            # Get final response after tool calls
            response = openai_service.chat_completion(messages)
            reply = response.choices[0].message.content
        else:
            # Normal conversation (no tools)
            reply = message.content
        
        # Save assistant's reply
        session_manager.add_message(session_id, "assistant", reply)
        
        return {"reply": reply}
    
    except Exception as e:
        logger.exception("Chat error")
        return JSONResponse(status_code=500, content={"error": str(e)})



# ---------------------------
# Spotify Search Endpoint
# ---------------------------
@app.get("/spotify/search")
def spotify_search(query: str, type_: str = "track"):
    """
    Direct Spotify search endpoint.x
    
    Args:
        query: Search query
        type_: Search type (track, artist, playlist, album)
        
    Returns:
        JSON list of formatted results
    """
    try:
        raw_results = spotify_service.search(query, type_)
        formatted_results = spotify_service.format_results(raw_results)
        return formatted_results
    except Exception as e:
        logger.exception("Spotify search error")
        return JSONResponse(status_code=500, content={"error": str(e)})



# ---------------------------
# Camera Snapshot Endpoint
# ---------------------------
@app.get("/camera/snapshot")
def camera_snapshot():
    """
    Capture a frame from the default camera.
    
    Returns:
        JSON with base64 encoded image
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="Cannot open camera")
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to grab frame")
    
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode frame")
    
    img_base64 = base64.b64encode(buf).decode("utf-8")
    return {"image_base64": img_base64}



# ---------------------------
# Herdora Vision Endpoints
# ---------------------------
@app.post("/get_hedora_text")
def get_herdora_text(body: HerdoraRequest):
    """
    Analyze an image using Herdora vision model.
    
    Args:
        body: Request with image_base64, prompt, and max_tokens
        
    Returns:
        JSON with analysis text
    """
    try:
        text = herdora_service.analyze_image(
            body.image_base64,
            body.prompt,
            body.max_tokens
        )
        return {"text": text}
    except Exception as e:
        logger.exception("Herdora analysis error")
        raise HTTPException(status_code=502, detail=f"Herdora request failed: {e}")



@app.post("/chat_from_hedora_text")
def chat_from_herdora_text(body: HerdoraTextRequest):
    """
    Convert Herdora mood description into friendly music-focused message.
    
    Args:
        body: Request with hedora_text (mood description)
        
    Returns:
        JSON with friendly conversational reply
    """
    try:
        reply = openai_service.create_friendly_message(body.hedora_text)
        return {"reply": reply}
    except Exception as e:
        logger.exception("Chat from Herdora text error")
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {e}")