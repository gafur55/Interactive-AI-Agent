"""
Text processing utilities for cleaning and formatting text.
"""

import re

def strip_links_for_tts(text: str) -> str:
    """
    Remove Spotify URLs from text before sending to TTS.
    
    Args:
        text: Input text that may contain Spotify links
        
    Returns:
        Cleaned text with Spotify URLs removed
        
    Example:
        >>> strip_links_for_tts("Check out this song (https://open.spotify.com/track/123)")
        "Check out this song"
    """
    return re.sub(r"\(https:\/\/open\.spotify\.com[^\)]+\)", "", text).strip()

def ensure_data_url(base64_string: str) -> str:
    """
    Ensure a base64 string has the proper data URL prefix.
    
    Args:
        base64_string: Base64 encoded image string
        
    Returns:
        Properly formatted data URL
        
    Example:
        >>> ensure_data_url("iVBORw0KGgo...")
        "data:image/jpeg;base64,iVBORw0KGgo..."
    """
    s = base64_string.strip()
    if s.startswith("data:image/"):
        return s
    return f"data:image/jpeg;base64,{s}"