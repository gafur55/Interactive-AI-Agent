"""
Configuration module for loading environment variables and app settings.
Centralizes all API keys and configuration in one place.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing from environment variables")
    
    # ElevenLabs Configuration (optional)
    ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
    
    # Spotify Configuration
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    # Herdora Configuration
    HERDORA_API_KEY = os.getenv("HERDORA_API_KEY")
    HERDORA_BASE_URL = "https://pygmalion.herdora.com/v1"
    HERDORA_MODEL = "Qwen/Qwen3-VL-235B-A22B-Instruct"
    
    # App Settings
    CORS_ORIGINS = ["*"]  # Configure this for production
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Create a singleton instance
config = Config()