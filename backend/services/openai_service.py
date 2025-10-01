"""
OpenAI service for Speech-to-Text (Whisper), Text-to-Speech, and Chat (GPT).
"""

import json
import logging
from io import BytesIO
from typing import List, Dict, Tuple, Optional
import openai
from config import config

logger = logging.getLogger("uvicorn.error")

# Configure OpenAI
openai.api_key = config.OPENAI_API_KEY

class OpenAIService:
    """Service for OpenAI API interactions"""
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        # Create standard OpenAI client
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.openai.com/v1"
        )
    
    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe audio to text using OpenAI Whisper.
        
        Args:
            audio_bytes: Raw audio file bytes
            filename: Original filename (used for format detection)
            
        Returns:
            Transcribed text
            
        Raises:
            Exception: If transcription fails
        """
        bio = BytesIO(audio_bytes)
        bio.name = filename
        
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=bio
        )
        return transcription.text
    
    def text_to_speech(self, text: str, voice: str = "nova") -> bytes:
        """
        Convert text to speech using OpenAI TTS.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Audio bytes (MP3 format)
            
        Raises:
            openai.APIError: If TTS request fails
        """
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        return response.read()
    
    def chat_completion(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Get a chat completion from GPT.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            model: Model to use for completion
            
        Returns:
            OpenAI chat completion response object
        """
        kwargs = {
            "model": model,
            "messages": messages
        }
        if tools:
            kwargs["tools"] = tools
        
        return openai.chat.completions.create(**kwargs)
    
    def create_friendly_message(self, mood_description: str) -> str:
        """
        Convert a mood description into a friendly, music-focused message.
        
        Args:
            mood_description: Long-form description of mood/photo
            
        Returns:
            Short, friendly conversational message
        """
        prompt = f"""
You are a friendly conversational assistant **with a love for music**.

Below is a paragraph that describes the mood of a photo.

Your task:
- Speak **directly to the person in the photo**—start with their name if provided,
or use a warm greeting like "Hey there!" or "Hi friend!" before the main thought.
- Keep it relaxed and natural (1–2 sentences).
- **Bring the chat back to music**—relate the mood to a rhythm, melody, playlist,
or invite them to share what they're listening to.
- Avoid repeating every detail; just capture the vibe and spark a music-centered conversation.

Mood paragraph:
{mood_description}

Return only the conversational message.
""".strip()
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

# Create a singleton instance
openai_service = OpenAIService()