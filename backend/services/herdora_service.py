"""
Herdora vision API service for image analysis.
Uses OpenAI-compatible API format.
"""

import openai
from config import config
from utils.text_utils import ensure_data_url

class HerdoraService:
    """Service for Herdora vision API"""
    
    def __init__(self):
        self.api_key = config.HERDORA_API_KEY
        self.base_url = config.HERDORA_BASE_URL
        self.model = config.HERDORA_MODEL
        
        if not self.api_key:
            raise RuntimeError("HERDORA_API_KEY is not configured")
        
        # Create OpenAI-compatible client for Herdora
        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def analyze_image(
        self,
        image_base64: str,
        prompt: str = "Describe this image.",
        max_tokens: int = 256
    ) -> str:
        """
        Analyze an image using Herdora's vision model.
        
        Args:
            image_base64: Base64 encoded image (with or without data URL prefix)
            prompt: Text prompt for the vision model
            max_tokens: Maximum tokens in response
            
        Returns:
            Text description from the vision model
            
        Raises:
            Exception: If the API request fails
            
        Example:
            >>> service.analyze_image("base64string...", "What mood is this?")
            "The person appears happy and relaxed..."
        """
        # Ensure proper data URL format
        data_url = ensure_data_url(image_base64)
        
        # Create vision request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            max_tokens=max_tokens,
        )
        
        # Extract text from response
        text = response.choices[0].message.content if response.choices else ""
        return text

# Create a singleton instance
herdora_service = HerdoraService()